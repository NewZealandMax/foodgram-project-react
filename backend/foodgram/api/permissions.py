from rest_framework import permissions


class RecipePermission(permissions.IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        print(request.query_params)
        return request.method in permissions.SAFE_METHODS or request.user == obj.author


class UserPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated or request.method == 'POST'      
