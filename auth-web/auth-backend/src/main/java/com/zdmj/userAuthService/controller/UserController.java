package com.zdmj.userAuthService.controller;

import com.zdmj.common.exception.ErrorCode;
import com.zdmj.common.exception.BusinessException;
import com.zdmj.common.model.Result;
import com.zdmj.userAuthService.dto.UserDTO;
import com.zdmj.userAuthService.dto.UserLoginDTO;
import com.zdmj.userAuthService.dto.UserLoginResponseDTO;
import com.zdmj.userAuthService.dto.UserRegisterDTO;
import com.zdmj.userAuthService.dto.UserResetPasswordDTO;
import com.zdmj.userAuthService.dto.UserUpdateDTO;
import com.zdmj.userAuthService.service.UserService;
import com.zdmj.userAuthService.service.VerificationCodeService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

/**
 * 用户控制器
 */
@Slf4j
@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final VerificationCodeService verificationCodeService;

    /**
     * 创建用户（用户注册）
     * 
     * @param registerDTO 注册信息
     * @return 注册结果
     */
    @PostMapping
    public Result<UserDTO> createUser(@Valid @RequestBody UserRegisterDTO registerDTO) {
        log.info("用户注册请求: {}", registerDTO.getUsername());
        UserDTO userDTO = userService.register(registerDTO);
        return Result.success("注册成功", userDTO);
    }

    /**
     * 根据ID查询用户信息
     * 
     * @param id 用户ID
     * @return 用户信息
     */
    @GetMapping("/{id}")
    public Result<UserDTO> getUserById(@PathVariable @Min(value = 1, message = "用户ID不能小于1") Long id) {
        log.info("查询用户信息: {}", id);
        UserDTO userDTO = userService.getUserById(id);
        return Result.success("查询成功", userDTO);
    }

    /**
     * 用户登录
     * 
     * @param loginDTO 登录凭证（用户名或邮箱、密码）
     * @return 登录结果
     */
    @PostMapping("/login")
    public Result<UserLoginResponseDTO> login(@Valid @RequestBody UserLoginDTO loginDTO) {
        log.info("用户登录请求: {}", loginDTO.getUsernameOrEmail());
        UserLoginResponseDTO response = userService.login(loginDTO);
        return Result.success("登录成功", response);
    }

    /**
     * 发送验证码
     * 
     * @param email 邮箱地址
     * @return 发送结果
     */
    @PostMapping("/verification-codes")
    public Result<Void> sendVerificationCode(
            @RequestParam @NotBlank(message = "邮箱不能为空") @Email(message = "邮箱格式不正确") String email) {
        log.info("发送验证码请求: {}", email);
        boolean success = verificationCodeService.sendVerificationCode(email);
        if (success) {
            return Result.success("验证码已发送到邮箱", null);
        } else {
            throw new BusinessException(ErrorCode.CAPTCHA_SEND_FAILED);
        }
    }

    /**
     * 重置密码（忘记密码时使用）
     * 
     * @param resetPasswordDTO 重置密码信息（包含邮箱、验证码、新密码）
     * @return 重置结果
     */
    @PutMapping("/password")
    public Result<Void> resetPassword(@Valid @RequestBody UserResetPasswordDTO resetPasswordDTO) {
        log.info("重置密码请求: email={}", resetPasswordDTO.getEmail());
        userService.resetPassword(resetPasswordDTO);
        return Result.success("密码修改成功", null);
    }

    /**
     * 更新当前登录用户的基本信息
     *
     * @param updateDTO 更新信息（姓名、电话、主页链接）
     * @return 更新后的用户信息
     */
    @PutMapping("/me")
    public Result<UserDTO> updateCurrentUser(@Valid @RequestBody UserUpdateDTO updateDTO) {
        log.info("更新当前用户信息请求");
        UserDTO userDTO = userService.updateCurrentUser(updateDTO);
        return Result.success("更新成功", userDTO);
    }

    /**
     * 验证用户名是否存在
     * 
     * @param username 用户名
     * @return 是否存在
     */
    @GetMapping("/validation/username")
    public Result<Boolean> validateUsername(@RequestParam String username) {
        log.info("检查用户名是否存在: {}", username);
        boolean exists = userService.existsByUsername(username);
        return Result.success(exists);
    }

    /**
     * 验证邮箱是否存在
     * 
     * @param email 邮箱
     * @return 是否存在
     */
    @GetMapping("/validation/email")
    public Result<Boolean> validateEmail(@RequestParam String email) {
        log.info("检查邮箱是否存在: {}", email);
        boolean exists = userService.existsByEmail(email);
        return Result.success(exists);
    }
}
