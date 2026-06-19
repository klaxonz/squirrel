from pydantic import BaseModel, EmailStr, Field, SecretStr, model_validator


class UserRegisterRequest(BaseModel):
    nickname: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None


class UserPasswordUpdateRequest(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(..., min_length=8)

    @model_validator(mode='after')
    def validate_passwords(self):
        if self.current_password.get_secret_value() == self.new_password.get_secret_value():
            raise ValueError('新密码不能与当前密码相同')
        return self


class UserConfigUpdate(BaseModel):
    settings: dict = Field(..., json_schema_extra={'example': {'showNsfw': False}})
    merge: bool | None = False

    @model_validator(mode='after')
    def validate_settings(self):
        allowed_keys = {'showNsfw', 'autoplay', 'autoplayNext', 'loop'}
        for key in self.settings:
            if key not in allowed_keys:
                raise ValueError(f'无效的配置项: {key}')
        if 'showNsfw' in self.settings and not isinstance(self.settings['showNsfw'], bool):
            raise ValueError('showNsfw必须是布尔值')
        if 'autoplay' in self.settings and not isinstance(self.settings['autoplay'], bool):
            raise ValueError('autoplay必须是布尔值')
        if 'autoplayNext' in self.settings and not isinstance(self.settings['autoplayNext'], bool):
            raise ValueError('autoplayNext必须是布尔值')
        if 'loop' in self.settings and not isinstance(self.settings['loop'], bool):
            raise ValueError('loop必须是布尔值')
        return self
