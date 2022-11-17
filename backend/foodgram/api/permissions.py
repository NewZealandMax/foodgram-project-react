from rest_framework import permissions


class RecipePermission(permissions.IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        return super().has_permission(request, view)
        #return request.method in permissions.SAFE_METHODS or request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or request.user == obj.author


class UserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated or request.method == 'POST'      
