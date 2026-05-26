package com.zdmj.common.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.PathMatchConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置类
 * 用于统一配置所有 Controller 的 API 前缀
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${api.prefix:/api}")
    private String apiPrefix;

    /**
     * 配置路径匹配，为所有 Controller 添加统一前缀
     */
    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.addPathPrefix(apiPrefix,
                c -> c.isAnnotationPresent(org.springframework.web.bind.annotation.RestController.class));
    }
}
