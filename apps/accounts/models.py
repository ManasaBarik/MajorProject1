from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra_fields):
        if not email: raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = "ADMINISTRATOR"
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        CITIZEN="CITIZEN"; BUSINESS_OWNER="BUSINESS_OWNER"; OFFICER="OFFICER"; ENGINEER="ENGINEER"; ADMINISTRATOR="ADMINISTRATOR"
    username = None
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CITIZEN, db_index=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()
    USERNAME_FIELD, REQUIRED_FIELDS = "email", ["name"]

class CitizenProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="citizen_profile")
    address=models.TextField(blank=True)
    city=models.CharField(max_length=100,blank=True)
    state=models.CharField(max_length=100,blank=True)
    pincode=models.CharField(max_length=12,blank=True)
    ward=models.CharField(max_length=80,blank=True)
    profile_photo=models.ImageField(upload_to="profiles/%Y/%m/",null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class OfficerProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="officer_profile")
    department=models.ForeignKey("departments.Department",on_delete=models.PROTECT,related_name="staff")
    employee_id=models.CharField(max_length=80,blank=True)
    designation=models.CharField(max_length=120,blank=True)
    phone=models.CharField(max_length=30,blank=True)
    available=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("department",),
                condition=Q(available=True),
                name="one_available_officer_per_department",
            ),
        ]

    @property
    def is_available(self):
        return self.available

class EngineerProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="engineer_profile")
    department=models.ForeignKey("departments.Department",on_delete=models.PROTECT,related_name="engineers")
    services=models.ManyToManyField("services.Service",blank=True,related_name="qualified_engineers")
    employee_id=models.CharField(max_length=80,blank=True)
    specialization=models.CharField(max_length=120,blank=True)
    available=models.BooleanField(default=True); workload=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    @property
    def is_available(self):
        return self.available
