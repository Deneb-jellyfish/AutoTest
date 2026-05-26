package com.zdmj.common.config;

import com.zdmj.common.cache.RedisUtil;
import com.zdmj.common.cache.RedisConstants;
import com.zdmj.common.context.UserContext;
import com.zdmj.common.context.UserHolder;
import com.zdmj.userAuthService.util.JwtUtil;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

/**
 * JWT认证过滤器
 */
@Slf4j
@RequiredArgsConstructor
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final RedisUtil redisCacheUtil;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        // 从请求头中获取Token
        String token = getTokenFromRequest(request);

        if (StringUtils.hasText(token) && JwtUtil.validateToken(token)) {
            try {
                Long userId = JwtUtil.getUserIdFromToken(token);
                String username = JwtUtil.getUsernameFromToken(token);

                if (userId != null && username != null) {
                    // 二次校验：Redis 中必须存在并且与当前 token 一致（支持单点登录/踢下线）
                    String tokenKey = RedisConstants.JWT_TOKEN_KEY + userId;
                    String storedToken = redisCacheUtil.getString(tokenKey);

                    if (storedToken != null && storedToken.equals(token)) {
                        UserContext userContext = UserContext.of(userId, username);
                        UserHolder.set(userContext);

                        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                                userContext,
                                null,
                                Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));
                        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                        SecurityContextHolder.getContext().setAuthentication(authentication);
                    } else {
                        log.warn("JWT Token在Redis中不存在或已失效: userId={}, username={}", userId, username);
                    }
                } else {
                    log.warn("JWT Token解析用户信息失败: userId={}, username={}", userId, username);
                }
            } catch (Exception e) {
                log.error("JWT认证失败: {}", e.getMessage(), e);
            }
        }
        filterChain.doFilter(request, response);
    }

    /**
     * 从请求头中获取Token
     * 支持两种格式：
     * 1. Authorization: Bearer <token>
     * 2. Authorization: <token>
     */
    private String getTokenFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        // 兼容没有Bearer前缀的情况
        return StringUtils.hasText(bearerToken) ? bearerToken : null;
    }
}
