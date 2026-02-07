# import json
# import uuid
#
# from django import forms
#
# from alpha_minio.alpha_minio_worker import alpha_mimio
#
# from .models import Star
#
#
# class StarForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields["stellar_object_type"].required = True
#
#     upload_image = forms.ImageField(required=False)
#
#     def save(self, commit=True):
#         instance = super().save(commit=commit)
#         if self.cleaned_data.get("upload_image"):
#             object_name = f"{str(uuid.uuid4())}"
#             resp = alpha_mimio.upload_file(
#                 object_name,
#                 self.cleaned_data.get("upload_image"),
#                 bucket_name="deepsky",
#             )
#             instance.img = {
#                 "object_name": resp.object_name,
#                 "bucket_name": resp.bucket_name,
#                 "etag": resp.etag,
#             }
#             instance.save()
#         return instance
#
#     class Meta:
#         model = Star
#         fields = (
#             "custom_id",
#             "title",
#             "area",
#             "constellation",
#             "comment",
#             "upload_image",
#             "stellar_object_type",
#         )
