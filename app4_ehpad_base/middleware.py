from app4_ehpad_base.forms import PublicPhoto


def get_new_public_photo_form(get_response):
    def middleware(request):
        request.public_photo_sent = None
        request.public_photo_form = PublicPhoto()
        if request.session.get('public_photo_success'):
            request.public_photo_sent = True
            request.session['public_photo_success'] = None
        response = get_response(request)
        return response
    return middleware
