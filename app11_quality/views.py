import io
import urllib.request

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.template.loader import render_to_string, get_template
from xhtml2pdf import pisa
from django.db.models.functions import Lower

from app11_quality.models import Image, Title, Protocol, Room, Message, TempMessage, Protocol_list, Tag
from app11_quality.models_qualite import Critere, Response
from django.http import FileResponse, HttpResponse, JsonResponse
import asyncio
from datetime import datetime
from app11_quality.forms import TagForm, ProtocolForm


# Here we define the private function which will be called by the websocket
def _message_rq():
    message = TempMessage.objects.last()
    if message:
        messages = {'messages': message.value, 'date': message.date.strftime("%m/%d/%Y, %H:%M:%S"),
                    'user': message.user,
                    'room': message.room.pk}
    else:
        messages = False
    return messages


# Here we define the function which will be called before we close the socket to empty temp model
def _clean_messages():
    x = TempMessage.objects.all()
    x.delete()

# Here we define async function which will get the messages from the temp model
async def ws_chat(socket):
    await socket.accept()  # Wait for a client to connect
    while True:
        try:
            message_rq = sync_to_async(_message_rq)  # Get the message from the client
            new_message = await message_rq()  # Create a new message with the newly received message
            if new_message:
                await socket.send_json({"new_messages": new_message})  # Send the message to the client
                await socket.receive_json()  # Wait for the client to receive the message
                clean_rq = sync_to_async(_clean_messages)  # Clean the messages
                await clean_rq()  # Clean the messages
            await asyncio.sleep(0.1)  # Wait for 1 second before going back to while loop
        except Exception as e:
            break
    await socket.close()  # Close the client


# Here we render the home-chat HTML template
def chat(request):
    return render(request, 'app11_quality/home-chat.html')


def getMessages(request, room):
    room_details = Room.objects.get(name=room)
    messages = Message.objects.filter(room=room_details.id)
    return JsonResponse({'messages': list(messages.values())})


# Here we create the function which will create a message
def send(request, room):
    if request.method == 'POST':
        username = request.POST['username']
        # room_id = request.POST['room_id']
        room_id = Room.objects.get(name=room)
        message = request.POST['message']
        if message != "":
            new_message = Message.objects.create(user=username, room=room_id, value=message)
            new_message.save()
            new_TempMessage = TempMessage.objects.create(user=username, room=room_id, value=message)
            new_TempMessage.save()
        return HttpResponse('Message was sent successfully')


# Here we check if the given name room exists in the database then, if it does, we render the chat HTML template
def room(request, room):
    ws = f'wss://{request.get_host()}:{request.META.get("SERVER_PORT")}/app11_quality/ws_chat/'
    username = request.GET.get('username')
    if Room.objects.filter(name=room).exists():
        room_details = Room.objects.get(name=room)
        messages = Message.objects.filter(room=room_details.id)
        context = {"room": room, "room_details": room_details, "username": username, "ws": ws,
                   "messages": list(messages.values())}
        return render(request, 'app11_quality/room-chat.html', context)
    else:
        return redirect('chat/')


# Here we define the function which will be called at the moment the user clicks the enter button
def enter(request):
    username = request.POST['username']
    # room = request.POST['room_name']
    try:
        room = Room.objects.get(name__iexact=request.POST['room_name'])
    except ObjectDoesNotExist:
        room = False
    if room:
        return redirect('chat/' + room.name + '/?username=' + username)
    else:
        new_room = Room.objects.create(name=request.POST['room_name'])
        new_room.save()
        return redirect('chat/' + request.POST['room_name'] + '/?username=' + username)


########################################################################################################################
# PROTOCOLS PART
########################################################################################################################


# Here we define the context dictionary for the template using the protocol model
def index(request):
    protocolsGen = Protocol.objects.filter(category='generic')
    protocolsSpe = Protocol.objects.filter(category='specific')
    context = {"protocolsGen": protocolsGen, "protocolsSpe": protocolsSpe}
    return render(request, 'app11_quality/protocols.html', context)


# Here we create the PDF object, using ReportLab Canvas
def toPdf(request, protocol_id):
    protocol = Protocol.objects.get(id=protocol_id)  # Get the protocol
    if protocol.category == "generic":  # If the protocol is generic
        template = get_template('app11_quality/generic_protocol.html')
    else:
        template = get_template('app11_quality/specific_protocol.html')
    html = template.render({"protocol": protocol})  # Render the template
    result = io.BytesIO()  # Create a BytesIO object which is a buffer for storing data
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-16')), result)  # Create the PDF object with the buffer result
    # ISO-8859-1
    if not pdf.err:  # If there is no error
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("Errors encountered")

    #
    # return FileResponse(buffer, as_attachment=True, filename='protocol_' + protocol.name + '.pdf')  # Return the PDF
    # # object as a file-like object


########################################################################################################################
# PROTOCOLS LIST DISPLAY PART
########################################################################################################################


def protocols_list(request, response_id=None):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    protocols = Protocol_list.objects.order_by('name')

    context = {"tagForm": TagForm(), "tags": Tag.objects.order_by(Lower('name')), "protocolForm": ProtocolForm()}

    response = None
    if response_id:
        response = Response.objects.get(id=response_id)
        context["response"] = response

    if request.method == 'POST':
        selected_tags = request.POST.getlist('tag_name')
        if selected_tags:
            protocols = Protocol_list.objects.filter(tag__name__in=selected_tags).distinct('id')
        else:
            protocols = Protocol_list.objects.all().distinct('id')

        context["selected_tags"] = selected_tags

        # Sélectionne un protocole et l'ajoute à un réponse
        if request.POST.get('selected') and response:
            selected_protocol = Protocol_list.objects.get(id=request.POST.get('selected'))
            response.protocols.add(selected_protocol)

        # Supprime un protocole d'une réponse
        elif request.POST.get('remove') and response:
            selected_protocol = Protocol_list.objects.get(id=request.POST.get('remove'))
            response.protocols.remove(selected_protocol)
            
        # Ajoute un tag au protocole
        else:
            tagForm = TagForm(request.POST)
            if tagForm.is_valid():
                forminfo = tagForm.save()
                tag = Tag.objects.get(id=forminfo.id)
                protocol_id = request.POST['protocol_id']
                protocol = Protocol_list.objects.get(id=protocol_id)
                protocol.tag.add(tag)
                protocol.save()

    context["protocols"] = protocols
    
    return render(request, 'app11_quality/protocols_list.html', context)


def dlProtocol(request, protocol_id):
    protocol = Protocol_list.objects.get(id=protocol_id)
    return HttpResponse(protocol.file, content_type='application/pdf')


def removeTagRelation(request, protocol_id, tag_id):
    protocol = Protocol_list.objects.get(id=protocol_id)
    tag = Tag.objects.get(id=tag_id)
    protocol.tag.remove(tag)
    protocol.save()
    return redirect('app11_quality protocols')


def deleteProtocol(request, protocol_id):
    protocol = Protocol_list.objects.get(id=protocol_id)
    protocol.delete()
    return redirect('app11_quality protocols')


def addExistingTag(request, protocol_id):
    if request.method == 'POST':
        if request.POST.get('tag_name'):
            tags = Tag.objects.filter(name__in=request.POST.getlist('tag_name')).values_list('id', flat=True)
            protocol = Protocol_list.objects.get(id=protocol_id)
            for tag in tags:
                protocol.tag.add(tag)
            protocol.save()
    return redirect('app11_quality protocols')


def addNewProtocol(request):
    if request.method == 'POST':
        name = request.POST['protocol_name']
        file = request.FILES['protocol_file']
        description = request.POST['protocol_description']
        protocol = Protocol_list.objects.create(name=name, file=file, description=description)
        protocol.save()
        return redirect('app11_quality protocols')

