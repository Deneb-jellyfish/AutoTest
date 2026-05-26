package com.zdmj.userAuthService.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 重置密码DTO
 */
@Data
public class UserResetPasswordDTO {

    /**
     * 邮箱地址（不能为空，需符合邮箱格式）
     */
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    /**
     * 验证码（不能为空，固定 6 位）
     */
    @NotBlank(message = "验证码不能为空")
    @Size(min = 6, max = 6, message = "验证码必须是6位数字")
    private String verificationCode;

    /**
     * 新密码（不能为空，长度 6-50 个字符）
     */
    @NotBlank(message = "新密码不能为空")
    @Size(min = 6, max = 50, message = "密码长度必须在6-50个字符之间")
    private String newPassword;
}
