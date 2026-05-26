package com.zdmj.userAuthService.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.zdmj.common.cache.RedisConstants;
import com.zdmj.userAuthService.entity.User;
import com.zdmj.userAuthService.enums.VerificationCodePurpose;
import com.zdmj.userAuthService.mapper.UserMapper;
import com.zdmj.userAuthService.service.EmailService;
import com.zdmj.userAuthService.service.VerificationCodeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.Random;
import java.util.concurrent.TimeUnit;

/**
 * 验证码服务实现类
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationCodeServiceImpl implements VerificationCodeService {

    private final StringRedisTemplate redisTemplate;
    private final EmailService emailService;
    private final UserMapper userMapper;
    private static final RedisScript<Long> VERIFY_AND_DELETE_SCRIPT = loadVerifyAndDeleteScript();

    private static RedisScript<Long> loadVerifyAndDeleteScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setLocation(new ClassPathResource("lua/verify_code_and_delete.lua"));
        script.setResultType(Long.class);
        return script;
    }

    @Override
    public boolean sendVerificationCode(String email) {
        VerificationCodePurpose purpose = resolvePurposeForSend(email);
        return sendVerificationCode(email, purpose);
    }

    @Override
    public boolean verifyCode(String email, String code, VerificationCodePurpose purpose) {
        try {
            String key = buildRedisKey(email, purpose);
            Long result = redisTemplate.execute(VERIFY_AND_DELETE_SCRIPT, Collections.singletonList(key), code);
            if (Long.valueOf(1L).equals(result)) {
                log.info("验证码验证成功: email={}, purpose={}", email, purpose);
                return true;
            }
            if (Long.valueOf(-1L).equals(result)) {
                log.warn("验证码错误: email={}, purpose={}", email, purpose);
                return false;
            }
            log.warn("验证码已过期或不存在: email={}, purpose={}", email, purpose);
            return false;
        } catch (Exception e) {
            log.error("验证验证码失败: email={}, purpose={}", email, purpose, e);
            return false;
        }
    }

    @Override
    public String generateCode() {
        Random random = new Random();
        int code = 100000 + random.nextInt(900000);
        return String.valueOf(code);
    }

    /**
     * 未注册邮箱视为注册场景，已注册邮箱视为重置密码场景（对外接口仅传 email，不改变 API）
     */
    private VerificationCodePurpose resolvePurposeForSend(String email) {
        boolean registered = userMapper.selectCount(new LambdaQueryWrapper<User>()
                .eq(User::getEmail, email)) > 0;
        return registered ? VerificationCodePurpose.RESET_PASSWORD : VerificationCodePurpose.REGISTER;
    }

    private boolean sendVerificationCode(String email, VerificationCodePurpose purpose) {
        try {
            String code = generateCode();
            String key = buildRedisKey(email, purpose);
            redisTemplate.opsForValue().set(key, code, RedisConstants.CODE_EXPIRE_TTL, TimeUnit.SECONDS);

            String content = String.format(
                    purpose.getEmailContentTemplate(),
                    code,
                    RedisConstants.CODE_EXPIRE_TTL / 60);
            emailService.sendEmail(email, purpose.getEmailSubject(), content);

            log.info("验证码已发送: email={}, purpose={}", email, purpose);
            return true;
        } catch (Exception e) {
            log.error("发送验证码失败: email={}, purpose={}", email, purpose, e);
            return false;
        }
    }

    private String buildRedisKey(String email, VerificationCodePurpose purpose) {
        return RedisConstants.verificationCodeKey(purpose.getRedisSuffix(), email);
    }
}
