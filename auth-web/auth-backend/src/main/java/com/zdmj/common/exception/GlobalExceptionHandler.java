package com.zdmj.common.exception;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import com.zdmj.common.model.Result;

import java.util.stream.Collectors;

/**
 * 全局异常处理器
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {
    /**
     * 处理业务异常
     * 
     * @param e 业务异常
     * @return Result对象
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Result<?>> handleBusinessException(BusinessException e) {
        log.warn("业务异常: {}", e.getMessage());
        HttpStatus status = resolveHttpStatus(e.getCode(), e.getMessage());
        return ResponseEntity.status(status).body(Result.error(e.getCode(), e.getMessage()));
    }

    /**
     * 处理参数校验异常（@RequestBody参数校验）
     * 
     * @param e 参数校验异常
     * @return Result对象
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleMethodArgumentNotValidException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": " + message);
    }

    /**
     * 处理参数校验异常（@ModelAttribute参数校验）
     * 
     * @param e 参数校验异常
     * @return Result对象
     */
    @ExceptionHandler(BindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleBindException(BindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": " + message);
    }

    /**
     * 处理参数校验异常（@RequestParam参数校验）
     * 
     * @param e 参数校验异常
     * @return Result对象
     */
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleConstraintViolationException(ConstraintViolationException e) {
        String message = e.getConstraintViolations().stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": " + message);
    }

    /**
     * 处理方法参数校验异常（如 @PathVariable / @RequestParam 的约束校验）
     *
     * @param e 方法参数校验异常
     * @return Result对象
     */
    @ExceptionHandler(HandlerMethodValidationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleHandlerMethodValidationException(HandlerMethodValidationException e) {
        String message = e.getAllErrors().stream()
                .map(error -> error.getDefaultMessage() != null ? error.getDefaultMessage() : error.toString())
                .collect(Collectors.joining(", "));
        log.warn("方法参数校验失败: {}", message);
        return Result.error(
                ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": " + message);
    }

    /**
     * 处理缺少必需的请求参数异常（@RequestParam 参数缺失）
     * 
     * @param e 缺少请求参数异常
     * @return Result对象
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleMissingServletRequestParameterException(MissingServletRequestParameterException e) {
        String parameterName = e.getParameterName();
        String parameterType = e.getParameterType();
        log.warn("缺少必需的请求参数: {} (类型: {})", parameterName, parameterType);
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": 缺少参数 " + parameterName);
    }

    /**
     * 处理请求参数类型不匹配异常（如将字符串传给需要数字的参数）
     * 
     * @param e 参数类型不匹配异常
     * @return Result对象
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleMethodArgumentTypeMismatchException(MethodArgumentTypeMismatchException e) {
        String parameterName = e.getName();
        String requiredType = e.getRequiredType() != null ? e.getRequiredType().getSimpleName() : "未知类型";
        Object value = e.getValue();
        log.warn("请求参数类型不匹配: {} = {} (期望类型: {})", parameterName, value, requiredType);
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                String.format("%s: %s 应为 %s 类型", ErrorCode.VALIDATION_ERROR.getMessage(), parameterName, requiredType));
    }

    /**
     * 处理JSON解析异常（如日期格式错误、类型不匹配、请求体为空等）
     * 
     * @param e JSON解析异常
     * @return Result对象
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleHttpMessageNotReadableException(HttpMessageNotReadableException e) {
        String message = e.getMessage();
        // 提取更友好的错误信息
        if (message != null) {
            // 处理请求体为空的情况
            if (message.contains("Required request body is missing")
                    || message.contains("I/O error while reading input message")
                    || message.contains("Required request body")) {
                log.warn("请求体为空");
                return Result.error(ErrorCode.REQUEST_BODY_ERROR.getCode(), ErrorCode.REQUEST_BODY_ERROR.getMessage());
            }
            // 处理日期格式错误
            if (message.contains("LocalDate") || message.contains("LocalDateTime")) {
                log.warn("日期格式错误: {}", message);
                return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                        ErrorCode.VALIDATION_ERROR.getMessage() + ": 日期格式错误");
            }
            // 处理JSON反序列化失败
            if (message.contains("Cannot deserialize")) {
                log.warn("JSON反序列化失败: {}", message);
                return Result.error(ErrorCode.VALIDATION_ERROR.getCode(), ErrorCode.VALIDATION_ERROR.getMessage());
            }
            // 处理JSON格式错误
            if (message.contains("JSON parse error") || message.contains("Unexpected character")) {
                log.warn("JSON格式错误: {}", message);
                return Result.error(ErrorCode.REQUEST_BODY_ERROR.getCode(), ErrorCode.REQUEST_BODY_ERROR.getMessage());
            }
        }
        log.warn("JSON解析失败: {}", message);
        return Result.error(ErrorCode.BAD_REQUEST.getCode(),
                ErrorCode.BAD_REQUEST.getMessage() + ": " + (message != null ? message : "未知错误"));
    }

    /**
     * 处理非法参数异常
     * 
     * @param e 非法参数异常
     * @return Result对象
     */
    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<?> handleIllegalArgumentException(IllegalArgumentException e) {
        log.warn("非法参数: {}", e.getMessage());
        return Result.error(ErrorCode.VALIDATION_ERROR.getCode(),
                ErrorCode.VALIDATION_ERROR.getMessage() + ": " + e.getMessage());
    }

    /**
     * 处理运行时异常
     * 
     * @param e 运行时异常
     * @return Result对象
     */
    @ExceptionHandler(RuntimeException.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<?> handleRuntimeException(RuntimeException e) {
        log.error("运行时异常: ", e);
        return Result.error(ErrorCode.INTERNAL_ERROR.getCode(),
                ErrorCode.INTERNAL_ERROR.getMessage() + ": " + e.getMessage());
    }

    /**
     * 处理所有其他异常
     * 
     * @param e 异常
     * @return Result对象
     */
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<?> handleException(Exception e) {
        log.error("系统异常: ", e);
        return Result.error(ErrorCode.SYSTEM_EXCEPTION.getCode(), ErrorCode.SYSTEM_EXCEPTION.getMessage());
    }

    /**
     * 根据业务错误码和错误信息推导 HTTP 状态码
     */
    private HttpStatus resolveHttpStatus(Integer code, String message) {
        if (code == null) {
            return HttpStatus.INTERNAL_SERVER_ERROR;
        }

        if (code.equals(ErrorCode.USER_NOT_LOGIN.getCode())) {
            return HttpStatus.UNAUTHORIZED;
        }
        if (code.equals(ErrorCode.NO_PERMISSION.getCode())) {
            return HttpStatus.FORBIDDEN;
        }
        // 1) “xxx不存在”类型业务错误 -> 404
        if (message != null && message.contains("不存在")) {
            return HttpStatus.NOT_FOUND;
        }
        // 2) “xxx操作失败”类型业务错误 -> 400
        if (message != null && message.contains("失败")) {
            return HttpStatus.BAD_REQUEST;
        }
        // 3) 其他业务错误 -> 400
        return HttpStatus.BAD_REQUEST;
    }

}
