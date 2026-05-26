package com.zdmj.userAuthService.service;

import com.zdmj.userAuthService.dto.UserDTO;
import com.zdmj.userAuthService.dto.UserLoginDTO;
import com.zdmj.userAuthService.dto.UserLoginResponseDTO;
import com.zdmj.userAuthService.dto.UserRegisterDTO;
import com.zdmj.userAuthService.dto.UserResetPasswordDTO;
import com.zdmj.userAuthService.dto.UserUpdateDTO;
import com.zdmj.userAuthService.entity.User;

/**
 * 用户服务接口
 */
public interface UserService {

    /**
     * 用户注册
     * 
     * @param registerDTO 注册信息
     * @return 用户信息
     */
    UserDTO register(UserRegisterDTO registerDTO);

    /**
     * 用户登录
     * 
     * @param loginDTO 登录信息
     * @return 登录响应（包含Token和用户信息）
     */
    UserLoginResponseDTO login(UserLoginDTO loginDTO);

    /**
     * 根据ID查询用户
     * 
     * @param id 用户ID
     * @return 用户信息
     */
    UserDTO getUserById(Long id);

    /**
     * 根据用户名查询用户
     * 
     * @param username 用户名
     * @return 用户实体
     */
    User getUserByUsername(String username);

    /**
     * 根据邮箱查询用户
     * 
     * @param email 邮箱
     * @return 用户实体
     */
    User getUserByEmail(String email);

    /**
     * 检查用户名是否存在
     * 
     * @param username 用户名
     * @return 是否存在
     */
    boolean existsByUsername(String username);

    /**
     * 检查邮箱是否存在
     * 
     * @param email 邮箱
     * @return 是否存在
     */
    boolean existsByEmail(String email);

    /**
     * 重置密码（忘记密码时使用）
     * 
     * @param resetPasswordDTO 重置密码信息（包含邮箱、验证码、新密码）
     */
    void resetPassword(UserResetPasswordDTO resetPasswordDTO);

    /**
     * 更新当前登录用户的基本信息
     *
     * @param updateDTO 更新信息（姓名、电话、主页链接）
     * @return 更新后的用户信息
     */
    UserDTO updateCurrentUser(UserUpdateDTO updateDTO);
}
