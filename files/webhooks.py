from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
from accounts.models import UserProfile


@csrf_exempt
def whatsapp_incoming(request):
    from_number = request.POST.get("From", "").replace("whatsapp:", "")

    try:
        profile = UserProfile.objects.get(whatsapp_number=from_number)
        profile.last_whatsapp_interaction = timezone.now()
        profile.save(update_fields=["last_whatsapp_interaction"])
    except UserProfile.DoesNotExist:
        pass

    return HttpResponse("OK")
