from .models import AuditLog


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        if request.user.is_authenticated:

            method = request.method

            if method in ["POST", "PUT", "PATCH", "DELETE"]:

                AuditLog.objects.create(
                    actor=request.user,
                    action=method,
                    path=request.path,
                )

        return response