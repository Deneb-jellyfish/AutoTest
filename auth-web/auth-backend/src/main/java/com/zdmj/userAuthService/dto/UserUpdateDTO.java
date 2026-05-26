package com.zdmj.userAuthService.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 用户信息更新DTO
 */
@Data
public class UserUpdateDTO {

    /**
     * 用户姓名（最大长度 100 个字符）
     */
    @Size(max = 100, message = "姓名长度不能超过100个字符")
    private String name;

    /**
     * 电话（最大长度 50 个字符）
     */
    @Size(max = 50, message = "电话长度不能超过50个字符")
    private String phone;

    /**
     * 主页链接（最大长度 255 个字符）
     */
    @Size(max = 255, message = "主页链接长度不能超过255个字符")
    private String website;
}

