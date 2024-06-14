accounts------------
import uuid
import json
from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.contrib.auth.hashers import check_password
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
# Create your models here.

def user_directory_path(instance, filename):
    return f'user_{instance.user.id}/{filename}'


class GenderChoice(models.TextChoices):
    MALE = 'Male', 'Male'
    FEMALE = 'Female', 'Female'
    OTHERS = 'Others', 'Others'

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)



class CustomUser(AbstractUser):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    org_type = models.CharField(max_length=150)
    org_name = models.CharField(max_length=250)
    org_sub_type = models.CharField(max_length=150)
    location_type = models.CharField(max_length=150)
    location_name = models.CharField(max_length=250)
    location_code = models.CharField(max_length=150)
    emp_code = models.CharField(max_length=150)
    department = models.CharField(max_length=250)
    designation = models.CharField(max_length=250)
    mobile = PhoneNumberField(null=False, blank=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    assigned_pol_no = models.CharField(max_length=1000)
    is_online = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_authenticator = models.BooleanField(default=False)
    is_site_admin = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_change_required = models.BooleanField(default=False)
    password_history_json = models.TextField(default='[]')
    is_sso_user = models.BooleanField(default=False, help_text="Is the user authenticated via SSO?")
    sso_provider = models.CharField(max_length=255, blank=True, null=True, help_text="SSO provider name")

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['mobile']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


    @property
    def password_history(self):
        return json.loads(self.password_history_json)

    @password_history.setter
    def password_history(self, value):
        self.password_history_json = json.dumps(value)

    def is_password_expired(self):
        if not self.last_password_change:
            return False
        return (timezone.now() - self.last_password_change).days >= 30

    def is_password_in_history(self, raw_password):
        for hashed_password in self.password_history:
            if check_password(raw_password, hashed_password):
                return True
        return False

    def set_password(self, raw_password):
        if self.is_password_in_history(raw_password):
            raise ValidationError("The new password cannot be the same as any of the last 3 password.")
        super().set_password(raw_password)
        self.last_password_change = timezone.now()
        password_history = self.password_history
        password_history.append(self.password)
        if len(self.password_history) > 3:
            password_history.pop(0)
        self.password_history = password_history

    def save(self, *args, **kwargs):
        if self.password_change_required and not self.is_password_expired():
            self.password_change_required = False
        super().save(*args, **kwargs)




class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="last modified at")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name="%(class)s_created_by",
                                   verbose_name="created by", null=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name="%(class)s_updated_by",
                                   verbose_name="last modified by", null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            user = kwargs.pop('user', None)
            self.created_by = user
        self.updated_by = kwargs.pop('user', None)
        super(BaseModel, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.id)



class UserProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
--------------audit-------------------
from django.db import models
from accounts.models import BaseModel,CustomUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# Create your models here.


class AuditLogType(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class AuditLogEntry(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.ForeignKey(AuditLogType, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    object_id = models.CharField(max_length=255)
    object_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    content_object = GenericForeignKey('object_type', 'object_id')
    details = models.TextField()

    def __str__(self):
        return f"{self.action_type} on {self.object_type} - {self.timestamp}"
------------------notifications--------------
from django.db import models
from accounts.models import BaseModel, CustomUser
# Create your models here.

class NotificationTemplate(BaseModel):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return self.name


class Notification(BaseModel):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"To: {self.recipient} - {self.template.name} ({'Read' if self.is_read else 'Unread'})"

--------------org--------------
from django.db import models
from accounts.models import BaseModel
from django.core.exceptions import ValidationError
# Create your models here.

class OrgType(models.TextChoices):
    MDINDIA = 'MDIndia', 'MDIndia'
    INSURANCE_COMPANY = 'Insurance Company', 'Insurance Company'
    BROKER = 'Broker', 'Broker'
    CORPORATE = 'Corporate', 'Corporate'

class LocationType(models.TextChoices):
    HO = 'HO', 'HO'
    RO = 'RO', 'RO'
    DO = 'DO', 'DO'
    UO = 'UO', 'UO'
    BRANCH = 'BRANCH', 'Branch'


class Organization(BaseModel):
    name = models.CharField(max_length=250,unique=True)
    org_type = models.CharField(max_length=150,choices=OrgType.choices)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


    def __str__(self):
        return self.name


class OrganizationSubType(BaseModel):
    org_type = models.CharField(max_length=150, choices=OrgType.choices)
    subtype = models.CharField(max_length=250, unique=True)

    def clean(self):
        if not Organization.objects.filter(org_type=self.org_type).exists():
            raise ValidationError(f"Organization Type with '{self.org_type}' does not exist.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Organization Sub Type"
        verbose_name_plural = "Organization Sub Types"

    def __str__(self):
        return f"{self.org_type} - {self.subtype}"


class Locations(BaseModel):
    org_type = models.CharField(max_length=150)
    org_name = models.CharField(max_length=250)
    location_type = models.CharField(max_length=150, choices=LocationType.choices)
    location_name = models.CharField(max_length=250)
    location_code = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"


class Department(BaseModel):
    name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name


class Designation(BaseModel):
    name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name = "Designation"
        verbose_name_plural = "Designations"


    def __str__(self):
        return self.name

---------------report-------------------
from django.db import models
from accounts.models import BaseModel, CustomUser

# Create your models here.

class Report(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    generated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/')

    def __str__(self):
        return self.name


--------roles---------------
from django.db import models
from accounts.models import BaseModel, CustomUser
# Create your models here.

class Application(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    base_url = models.URLField(blank=True, null=True, help_text="Base URL for the application")

    def __str__(self):
        return self.name


class Permission(BaseModel):
    name = models.CharField(max_length=255)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.application.name}"


class Role(BaseModel):
    name = models.CharField(max_length=255)
    permissions = models.ManyToManyField(Permission)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.application.name}"




class UserRole(BaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'role', 'application')

    def get_absolute_url(self):
        if self.application.base_url:
            return f"{self.application.base_url}/user/{self.user.username}"
        else:
            return "/profile/"

    def __str__(self):
        return f"{self.user.username} - {self.role.name} - {self.application.name}"

--------------teams---------------
from django.db import models
from accounts.models import BaseModel,CustomUser
# Create your models here.




class Team(BaseModel):
    name = models.CharField(max_length=150)
    description = models.TextField()
    users = models.ManyToManyField(CustomUser, related_name="teams")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def get_user_ids(self):
        return list(self.users.values_list("id", flat=True))

    def get_usernames(self):
        return list(self.users.values_list("username", flat=True))


