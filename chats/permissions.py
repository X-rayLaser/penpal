from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user


class IsChatOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.human


def IsOwnerOfParent(parent_attr):
    class IsOwnerOfParentPermission(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            parent = getattr(obj, parent_attr)
            return request.useer == parent.user
    return IsOwnerOfParentPermission
