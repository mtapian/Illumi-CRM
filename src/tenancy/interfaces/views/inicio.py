from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from shared.interfaces.avisos import avisos


@login_required
def dashboard(request):
    return render(
        request,
        "tenancy/dashboard.html",
        {
            "primeros_pasos": request.session.get("primeros_pasos", False),
            "avisos": avisos.para(request),
        },
    )
