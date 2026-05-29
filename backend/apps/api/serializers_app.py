# coding:utf-8
# iSpaceDoc DRF serializers

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer,SerializerMethodField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from backend.apps.doc.models import Doc,DocTemp,DocHistory,Image,ImageGroup,Attachment
from backend.apps.admin.models import RegisterCode


# 用户序列化器
class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
                'id', 'last_login', 'is_superuser', 'username', 'email', 'date_joined', 'is_active', 'first_name'
            )

# 注册邀请码序列化器
class RegisterCodeSerializer(ModelSerializer):
    status = serializers.SerializerMethodField(label="状态")

    class Meta:
        model = RegisterCode
        fields = ('__all__')

    def get_status(self,obj):
        current_date = timezone.now().date()
        if obj.used_cnt >= obj.all_cnt:
            return _('使用次数已满')
        elif obj.expire_date is not None and obj.expire_date < current_date:
            return _('已到期')
        else:
            return _('有效')

# 文档序列化器
class DocSerializer(ModelSerializer):

    modify_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = Doc
        fields = ('__all__')


# 文档历史序列化器
class DocHistorySerializer(ModelSerializer):
    username = serializers.SerializerMethodField(label="用户名")
    class Meta:
        model = DocHistory
        fields = ('__all__')

    def get_username(self,obj):
        return obj.create_user.username


# 文档模板序列化器
class DocTempSerializer(ModelSerializer):
    class Meta:
        model = DocTemp
        fields = ('__all__')

# 图片序列化器
class ImageSerializer(ModelSerializer):
    username = serializers.SerializerMethodField(label="用户名")
    class Meta:
        model = Image
        fields = ('__all__')

    def get_username(self,obj):
        return obj.user.username

# 图片分组序列化器
class ImageGroupSerializer(ModelSerializer):
    class Meta:
        model = ImageGroup
        fields = ('__all__')

# 附件序列化器
class AttachmentSerializer(ModelSerializer):
    file_path = serializers.CharField()
    username = serializers.SerializerMethodField(label="用户名")

    class Meta:
        model = Attachment
        fields = ('__all__')

    def get_username(self,obj):
        return obj.user.username
