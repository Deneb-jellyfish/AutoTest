package com.zdmj.common.util;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;

/**
 * 日期时间工具类
 * 统一处理时区相关的日期时间操作
 * 
 * 说明：
 * - 数据库使用 TIMESTAMP WITH TIME ZONE（带时区）
 * - Java业务代码使用 LocalDateTime（本地时间，基于JVM时区）
 * - 当JVM时区设置为Asia/Shanghai时，LocalDateTime.now()会自动使用该时区
 */
public class DateTimeUtil {

    /**
     * 应用默认时区：Asia/Shanghai（UTC+8）
     */
    private static final ZoneId DEFAULT_ZONE_ID = ZoneId.of("Asia/Shanghai");

    /**
     * 获取当前时间（基于应用默认时区）
     * 用于创建时间和更新时间字段
     * 
     * @return 当前时间的LocalDateTime（基于Asia/Shanghai时区）
     */
    public static LocalDateTime now() {
        // LocalDateTime.now() 会使用JVM的默认时区
        // 如果JVM时区已设置为Asia/Shanghai，则返回的就是该时区的时间
        return LocalDateTime.now(DEFAULT_ZONE_ID);
    }

    /**
     * 将LocalDateTime转换为指定时区的ZonedDateTime
     * 
     * @param localDateTime 本地时间
     * @return 带时区的时间
     */
    public static ZonedDateTime toZonedDateTime(LocalDateTime localDateTime) {
        return localDateTime.atZone(DEFAULT_ZONE_ID);
    }

    /**
     * 将ZonedDateTime转换为LocalDateTime（基于应用默认时区）
     * 
     * @param zonedDateTime 带时区的时间
     * @return 本地时间
     */
    public static LocalDateTime toLocalDateTime(ZonedDateTime zonedDateTime) {
        return zonedDateTime.withZoneSameInstant(DEFAULT_ZONE_ID).toLocalDateTime();
    }

    /**
     * 获取当前时区ID
     * 
     * @return 时区ID
     */
    public static ZoneId getDefaultZoneId() {
        return DEFAULT_ZONE_ID;
    }
}
