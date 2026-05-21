package com.zdmj.userAuthService.service;

/**
 * 验证码服务接口
 */
public interface VerificationCodeService {

    /**
     * 发送验证码到邮箱
     * 
     * @param email 邮箱地址
     * @return 是否发送成功
     */
    boolean sendVerificationCode(String email);

    /**
     * 验证验证码
     * 
     * @param email 邮箱地址
     * @param code  验证码
     * @return 是否验证通过
     */
    boolean verifyCode(String email, String code);

    /**
     * 生成6位数字验证码
     * 
     * @return 验证码
     */
    String generateCode();
}
