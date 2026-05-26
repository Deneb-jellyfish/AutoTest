package com.zdmj.common.config;

import com.zdmj.userAuthService.util.JwtUtil;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

@Configuration
public class JwtConfig {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expire-days:7}")
    private int expireDays;

    @PostConstruct
    public void initJwtUtil() {
        JwtUtil.init(secret, expireDays);
    }
}
