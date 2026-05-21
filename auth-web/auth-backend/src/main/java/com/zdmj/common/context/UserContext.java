package com.zdmj.common.context;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户上下文信息
 * 存储当前登录用户的完整信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserContext {

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 用户名
     */
    private String username;

    /**
     * 邮箱
     */
    private String email;

    /**
     * 创建用户上下文
     * 
     * @param userId   用户ID
     * @param username 用户名
     * @return 用户上下文
     */
    public static UserContext of(Long userId, String username) {
        return new UserContext(userId, username, null);
    }

    /**
     * 创建用户上下文（包含邮箱）
     * 
     * @param userId   用户ID
     * @param username 用户名
     * @param email    邮箱
     * @return 用户上下文
     */
    public static UserContext of(Long userId, String username, String email) {
        return new UserContext(userId, username, email);
    }
}
