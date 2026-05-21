package com.zdmj.userAuthService.service;

/**
 * 邮件服务接口
 */
public interface EmailService {

    /**
     * 发送邮件
     * 
     * @param to      收件人邮箱
     * @param subject 邮件主题
     * @param content 邮件内容
     */
    void sendEmail(String to, String subject, String content);
}
