package com.zdmj.userAuthService.enums;

import lombok.Getter;

/**
 * 验证码用途：注册与重置密码分别存储，互不通用
 */
@Getter
public enum VerificationCodePurpose {

    REGISTER("register", "注册验证码", "您的注册验证码是：%s，有效期%d分钟，请勿泄露给他人。"),
    RESET_PASSWORD("reset", "重置密码验证码", "您正在重置密码，验证码是：%s，有效期%d分钟，请勿泄露给他人。如非本人操作请忽略。");

    private final String redisSuffix;
    private final String emailSubject;
    private final String emailContentTemplate;

    VerificationCodePurpose(String redisSuffix, String emailSubject, String emailContentTemplate) {
        this.redisSuffix = redisSuffix;
        this.emailSubject = emailSubject;
        this.emailContentTemplate = emailContentTemplate;
    }
}
