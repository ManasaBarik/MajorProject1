from django.db import models


class AuditLog(models.Model):
	user = models.ForeignKey(
		"accounts.User", null=True, on_delete=models.SET_NULL,
		related_name="audit_events",
	)
	action = models.CharField(max_length=100)
	entity = models.CharField(max_length=100)
	entity_id = models.CharField(max_length=64)
	metadata = models.JSONField(default=dict, blank=True)
	old_value = models.JSONField(null=True, blank=True)
	new_value = models.JSONField(null=True, blank=True)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

	@property
	def actor(self):
		return self.user

	@property
	def entity_type(self):
		return self.entity
