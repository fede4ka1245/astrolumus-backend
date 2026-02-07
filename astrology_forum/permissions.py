from rest_framework.permissions import BasePermission, SAFE_METHODS


class ImageCanDelete(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "DELETE":
            if request.user and (request.user == obj.creator or request.user.is_staff or request.user.is_superuser):
                return True
        return False


class IsAuthorOrIsAdminOrCreateReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        safe = list(SAFE_METHODS)
        safe.append('POST')  # allow to create (user creator does not exist here)

        if request.method in safe or request.user and (
                request.user == obj.user or request.user.is_staff or request.user.is_superuser):
            return True
        return False


class IsAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and (request.user == obj.user or request.user.is_staff or request.user.is_superuser):
            return True
        return False

