package com.zdmj.common.exception;

import lombok.Getter;

/**
 * 统一错误码定义
 * 用于统一管理用户认证相关业务错误码
 */
@Getter
public enum ErrorCode {

    // ========== HTTP状态码 ==========
    BAD_REQUEST(400, "请求参数错误"),
    INTERNAL_ERROR(500, "服务器内部错误"),

    // ========== 通用错误 1xxx ==========
    VALIDATION_ERROR(1001, "参数校验失败"),
    USER_NOT_LOGIN(1002, "用户未登录"),
    NO_PERMISSION(1003, "无权操作"),
    REQUEST_BODY_ERROR(1004, "请求体错误，请提供有效的JSON数据"),
    SYSTEM_EXCEPTION(1008, "系统异常，请联系管理员"),

    // ========== 用户认证相关 (2xxx) ==========
    USER_ALREADY_EXISTS(2001, "用户名已存在"),
    USER_EMAIL_EXISTS(2002, "邮箱已被注册"),
    CAPTCHA_ERROR(2003, "验证码错误或已过期"),
    USER_REGISTER_FAILED(2004, "用户注册失败"),
    USER_PASSWORD_WRONG(2005, "用户名或密码错误"),
    USER_NOT_FOUND(2006, "用户不存在"),
    USER_EMAIL_NOT_REGISTERED(2007, "该邮箱未注册"),
    PASSWORD_CHANGE_FAILED(2008, "密码修改失败"),
    CAPTCHA_SEND_FAILED(2009, "验证码发送失败，请稍后重试");

    private final Integer code;
    private final String message;

    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
