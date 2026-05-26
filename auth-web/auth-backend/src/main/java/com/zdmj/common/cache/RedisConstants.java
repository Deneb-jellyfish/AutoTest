package com.zdmj.common.cache;

public class RedisConstants {
    // 验证码前缀（后接用途 register / reset 与邮箱）
    public static final String VERIFICATION_CODE_KEY = "verification:code:";
    // 验证码过期时间（秒）
    public static final int CODE_EXPIRE_TTL = 10 * 60;

    public static String verificationCodeKey(String purposeSuffix, String email) {
        return VERIFICATION_CODE_KEY + purposeSuffix + ":" + email;
    }

    // 会话缓存前缀
    public static final String CONVERSATION_KEY = "conversation:";
    // 会话缓存过期时间（秒）
    public static final int CONVERSATION_TTL = 60 * 60;

    // 会话消息缓存前缀
    public static final String CONVERSATION_MESSAGES_KEY = "conversation:messages:";
    // 会话消息缓存过期时间（秒）
    public static final int CONVERSATION_MESSAGES_TTL = 60 * 60;

    // 空值标记前缀（用于防止缓存穿透）
    public static final String NULL_VALUE_KEY = "null:value:";

    // 对话消息缓存前缀
    public static final String CONVERSATION_MESSAGE_KEY = "conversation:prompt:message:";
    // 对话消息缓存过期时间（秒）
    public static final int CONVERSATION_MESSAGE_TTL = 60 * 60;

    // 流式消息缓存前缀
    public static final String STREAMING_MESSAGE_KEY = "streaming:message:";
    // 流式消息缓存过期时间（秒）
    public static final int STREAMING_MESSAGE_TTL = 60 * 60;

    // JWT Token缓存前缀
    public static final String JWT_TOKEN_KEY = "jwt:token:";
    // JWT Token过期时间（秒）- 7天
    public static final int JWT_TOKEN_TTL = 7 * 24 * 60 * 60;

    // 岗位详情缓存前缀
    public static final String JOB_DETAIL_KEY = "job:detail:";
    // 岗位详情缓存过期时间（秒）- 10 分钟
    public static final int JOB_DETAIL_TTL = 10 * 60;
    // 岗位不存在时的空值标记 TTL（秒）
    public static final int JOB_DETAIL_NULL_TTL = 60;

}
