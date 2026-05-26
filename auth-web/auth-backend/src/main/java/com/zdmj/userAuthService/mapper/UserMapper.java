package com.zdmj.userAuthService.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zdmj.userAuthService.entity.User;
import org.apache.ibatis.annotations.Mapper;

/**
 * 用户Mapper接口
 * 继承 MyBatis-Plus 的 BaseMapper，自动拥有基础的 CRUD 方法：
 * - insert(entity) - 插入（自动回填ID）
 * - selectById(id) - 根据ID查询
 * - updateById(entity) - 根据ID更新
 * - deleteById(id) - 根据ID删除
 * - selectOne(wrapper) - 条件查询单个
 * - selectList(wrapper) - 条件查询列表
 * - selectCount(wrapper) - 条件计数
 * - update(wrapper) - 条件更新
 */

@Mapper
public interface UserMapper extends BaseMapper<User> {
    // 所有查询都可以通过 Service 层使用 QueryWrapper 实现，无需定义额外方法
}
