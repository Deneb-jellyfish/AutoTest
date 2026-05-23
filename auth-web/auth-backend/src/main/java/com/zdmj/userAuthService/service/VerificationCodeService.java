package com.zdmj.userAuthService.service;

import com.zdmj.userAuthService.enums.VerificationCodePurpose;

/**
 * 验证码服务接口
 */
public interface VerificationCodeService {

    /**
     * 发送验证码到邮箱（根据邮箱是否已注册自动区分注册 / 重置密码用途，接口不变）
     *
     * @param email 邮箱地址
     * @return 是否发送成功
     */
    boolean sendVerificationCode(String email);

    /**
     * 按用途验证验证码
     *
     * @param email   邮箱地址
     * @param code    验证码
     * @param purpose 验证码用途
     * @return 是否验证通过
     */
    boolean verifyCode(String email, String code, VerificationCodePurpose purpose);

    /**
     * 生成6位数字验证码
     *
     * @return 验证码
     */
    String generateCode();
}
