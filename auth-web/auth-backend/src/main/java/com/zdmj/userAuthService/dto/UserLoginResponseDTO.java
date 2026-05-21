package com.zdmj.userAuthService.dto;

import lombok.Data;

/**
 * 用户登录响应DTO（包含Token和用户信息）
 */
@Data
public class UserLoginResponseDTO {

    /**
     * JWT Token
     */
    private String token;

    /**
     * 用户信息
     */
    private UserDTO user;
}
