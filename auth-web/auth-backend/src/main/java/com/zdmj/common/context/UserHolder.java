package com.zdmj.common.context;

import org.springframework.core.NamedThreadLocal;

import com.zdmj.common.exception.BusinessException;
import com.zdmj.common.exception.ErrorCode;

/**
 * 用户信息持有者
 */
public class UserHolder {

    private UserHolder(){}

    /**
     * 使用NamedThreadLocal存储用户上下文信息
     */
    private static final NamedThreadLocal<UserContext> USER_CONTEXT = new NamedThreadLocal<>("zdmj-user-context");

    /**
     * 设置当前用户上下文
     * 
     * @param userContext 用户上下文
     */
    public static void set(UserContext userContext) {
        if (userContext == null) {
            USER_CONTEXT.remove();
            return;
        }
        USER_CONTEXT.set(userContext);
    }

    /**
     * 获取当前用户上下文
     * 
     * @return 用户上下文，如果未设置返回null
     */
    public static UserContext get() {
        return USER_CONTEXT.get();
    }

    /**
     * 获取当前用户ID
     * 
     * @return 用户ID，如果未登录返回null
     */
    public static Long getUserId() {
        UserContext context = USER_CONTEXT.get();
        return context == null ? null : context.getUserId();
    }

    /**
     * 获取当前用户名
     * 
     * @return 用户名，如果未登录返回null
     */
    public static String getUsername() {
        UserContext context = USER_CONTEXT.get();
        return context == null ? null : context.getUsername();
    }

    /**
     * 获取当前用户邮箱
     * 
     * @return 邮箱，如果未登录返回null
     */
    public static String getEmail() {
        UserContext context = USER_CONTEXT.get();
        return context == null ? null : context.getEmail();
    }
 
    /**
     * 检查当前用户是否已登录
     * 
     * @return 是否已登录
     */
    public static boolean isAuthenticated() {
        return USER_CONTEXT.get() != null;
    }

    /**
     * 要求用户必须已登录，返回用户ID
     * 如果用户未登录，抛出BusinessException异常
     * 
     * @return 用户ID
     * @throws BusinessException 如果用户未登录
     */
    public static Long requireUserId() {
        Long userId = getUserId();
        if (userId == null) {
            throw new BusinessException(ErrorCode.USER_NOT_LOGIN);
        }
        return userId;
    }

    /**
     * 清除当前线程的用户上下文
     * 必须在请求结束后调用，避免内存泄漏
     */
    public static void clear() {
        USER_CONTEXT.remove();
    }
}
