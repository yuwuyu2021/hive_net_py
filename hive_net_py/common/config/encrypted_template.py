"""
加密模板模块
"""
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .template import ConfigTemplate, TemplateManager, TemplateError
from .encrypted import EncryptedConfigLoader, create_encrypted_loader
from .base import ConfigLoader


class EncryptedTemplate(ConfigTemplate):
    """加密配置模板"""
    
    def __init__(
        self,
        template: Union[str, Dict[str, Any]],
        password: str,
        variables: Optional[Dict[str, Any]] = None,
        parent: Optional['ConfigTemplate'] = None
    ):
        """
        初始化加密模板
        
        Args:
            template: 模板内容
            password: 加密密码
            variables: 变量字典
            parent: 父模板
        """
        super().__init__(template, variables, parent)
        self.password = password
    
    def save(self, path: Path, loader: ConfigLoader) -> None:
        """
        保存加密模板
        
        Args:
            path: 保存路径
            loader: 基础加载器
        """
        try:
            # 创建加密加载���
            encrypted_loader = create_encrypted_loader(
                path.suffix.lstrip('.'),
                self.password
            )
            
            # 保存模板
            encrypted_loader.save(self.template, path)
        except Exception as e:
            raise TemplateError(f"Failed to save encrypted template: {e}")


class EncryptedTemplateManager(TemplateManager):
    """加密模板管理器"""
    
    def __init__(
        self,
        template_dir: Optional[Path] = None,
        password: Optional[str] = None
    ):
        """
        初始化管理器
        
        Args:
            template_dir: 模板目录
            password: 加密密码
        """
        super().__init__(template_dir)
        self.password = password
    
    def load_encrypted_template(
        self,
        name: str,
        loader: ConfigLoader,
        password: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        parent: Optional[str] = None
    ) -> EncryptedTemplate:
        """
        加载加密模板
        
        Args:
            name: 模板名称
            loader: 基础加载器
            password: 加密密码
            variables: 变量字典
            parent: 父模板名称
        
        Returns:
            加���模板
        """
        try:
            template_path = self.template_dir / name
            if not template_path.exists():
                raise TemplateError(f"Template not found: {name}")
            
            # 创建加密加载器
            password = password or self.password
            if not password:
                raise TemplateError("Password is required")
            
            encrypted_loader = create_encrypted_loader(
                template_path.suffix.lstrip('.'),
                password
            )
            
            # 加载模板内容
            template_content = encrypted_loader.load(template_path)
            
            # 获取父模板
            parent_template = None
            if parent:
                if parent not in self.templates:
                    raise TemplateError(f"Parent template not found: {parent}")
                parent_template = self.templates[parent]
            
            # 创建模板
            template = EncryptedTemplate(
                template_content,
                password,
                variables,
                parent_template
            )
            
            self.templates[name] = template
            return template
        except Exception as e:
            raise TemplateError(f"Failed to load encrypted template: {e}")
    
    def save_encrypted_template(
        self,
        name: str,
        template: Dict[str, Any],
        loader: ConfigLoader,
        password: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        保存加密模板
        
        Args:
            name: 模板名称
            template: 模板内容
            loader: 基础加载器
            password: 加密密码
            variables: 变量字典
        """
        try:
            template_path = self.template_dir / name
            
            # 创建加密模板
            password = password or self.password
            if not password:
                raise TemplateError("Password is required")
            
            encrypted_template = EncryptedTemplate(
                template,
                password,
                variables
            )
            
            # 保存模板
            encrypted_template.save(template_path, loader)
            
            # 添加到管理器
            self.templates[name] = encrypted_template
        except Exception as e:
            raise TemplateError(f"Failed to save encrypted template: {e}")
    
    def encrypt_existing_template(
        self,
        name: str,
        password: Optional[str] = None
    ) -> None:
        """
        加密现有模板
        
        Args:
            name: 模板名称
            password: 加密密码
        """
        try:
            template = self.get_template(name)
            if isinstance(template, EncryptedTemplate):
                raise TemplateError("Template is already encrypted")
            
            # 创建加密模板
            password = password or self.password
            if not password:
                raise TemplateError("Password is required")
            
            encrypted_template = EncryptedTemplate(
                template.template,
                password,
                template.variables,
                template.parent
            )
            
            # 保存模板
            template_path = self.template_dir / name
            encrypted_template.save(template_path, template.loader)
            
            # 更新管理器
            self.templates[name] = encrypted_template
        except Exception as e:
            raise TemplateError(f"Failed to encrypt template: {e}")
    
    def decrypt_template(
        self,
        name: str,
        password: Optional[str] = None
    ) -> None:
        """
        解密模板
        
        Args:
            name: 模板名称
            password: 解密密码
        """
        try:
            template = self.get_template(name)
            if not isinstance(template, EncryptedTemplate):
                raise TemplateError("Template is not encrypted")
            
            # 验证密码
            password = password or self.password
            if not password:
                raise TemplateError("Password is required")
            if password != template.password:
                raise TemplateError("Invalid password")
            
            # 创建普通模板
            decrypted_template = ConfigTemplate(
                template.template,
                template.variables,
                template.parent
            )
            
            # 保存模板
            template_path = self.template_dir / name
            template.loader.save(template.template, template_path)
            
            # 更新管理器
            self.templates[name] = decrypted_template
        except Exception as e:
            raise TemplateError(f"Failed to decrypt template: {e}")
    
    def is_encrypted(self, name: str) -> bool:
        """
        检查模板是否加密
        
        Args:
            name: 模板名称
        
        Returns:
            是否加密
        """
        try:
            template = self.get_template(name)
            return isinstance(template, EncryptedTemplate)
        except Exception:
            return False 