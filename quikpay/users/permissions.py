from rest_framework import permissions



class IsNotAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and not request.user.is_authenticated)
    

class IsAccountActive(permissions.BasePermission): 

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.status == 'active'