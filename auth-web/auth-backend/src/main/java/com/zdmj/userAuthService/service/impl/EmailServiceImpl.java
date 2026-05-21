package com.zdmj.userAuthService.service.impl;

import com.zdmj.userAuthService.service.EmailService;
import jakarta.mail.internet.MimeMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

/**
 * 邮件服务实现类
 */
@Slf4j
@Service
public class EmailServiceImpl implements EmailService {

    private final JavaMailSender mailSender;
    private final String fromEmail;

    /**
     * 构造函数注入（推荐方式）
     *
     * @param mailSender 邮件发送器
     * @param fromEmail 发件人邮箱（从配置文件读取）
     */
    public EmailServiceImpl(JavaMailSender mailSender, @Value("${spring.mail.username}") String fromEmail) {
        this.mailSender = mailSender;
        this.fromEmail = fromEmail;
    }

    @Override
    public void sendEmail(String to, String subject, String content) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

            // 设置发件人（与SMTP认证用户名一致）
            helper.setFrom(fromEmail);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(content, true); // false表示纯文本，true表示HTML

            mailSender.send(message);
            log.info("邮件发送成功: To={}, From={}", to, fromEmail);
        } catch (Exception e) {
            log.error("邮件发送失败: To={}, From={}, Error={}", to, fromEmail, e.getMessage(), e);
            throw new RuntimeException("邮件发送失败", e);
        }
    }
}
