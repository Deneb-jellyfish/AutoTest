package com.zdmj.common.config;

import java.io.IOException;

import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import com.zdmj.common.context.UserHolder;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestContextCleanupFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        // 清理用户上下文和Security上下文
        UserHolder.clear();
        SecurityContextHolder.clearContext();

        try {
            filterChain.doFilter(request, response);
        } finally {
            UserHolder.clear();
            SecurityContextHolder.clearContext();
        }

    }

    @Override
    protected boolean shouldNotFilterAsyncDispatch() {
        return false;
    }

}
