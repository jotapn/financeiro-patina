import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import AiAssistantLog, ChatMessage, ChatSession
from .services import build_agent_for_user, get_model_status


def _simple_pdf_bytes(lines):
    escaped_lines = []
    for line in lines:
        safe = (
            str(line)
            .replace('\\', '\\\\')
            .replace('(', '\\(')
            .replace(')', '\\)')
        )
        escaped_lines.append(safe)
    y = 780
    stream_lines = ['BT', '/F1 11 Tf', '40 800 Td']
    for line in escaped_lines:
        stream_lines.append(f'0 {y - 800} Td ({line[:100]}) Tj')
        y -= 16
        if y < 40:
            break
    stream_lines.append('ET')
    stream = '\n'.join(stream_lines).encode('latin-1', errors='ignore')
    objects = []
    objects.append(b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n')
    objects.append(b'2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n')
    objects.append(b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n')
    objects.append(f'4 0 obj << /Length {len(stream)} >> stream\n'.encode('latin-1') + stream + b'\nendstream endobj\n')
    objects.append(b'5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n')
    header = b'%PDF-1.4\n'
    body = bytearray(header)
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body.extend(obj)
    xref_offset = len(body)
    body.extend(f'xref\n0 {len(offsets)}\n'.encode('latin-1'))
    body.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        body.extend(f'{offset:010d} 00000 n \n'.encode('latin-1'))
    body.extend(f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF'.encode('latin-1'))
    return bytes(body)


@login_required
def chat_home(request):
    sessions = ChatSession.objects.filter(user=request.user).prefetch_related('messages')
    current_session = sessions.first()
    return render(request, 'ai_assistant/chat.html', {'sessions': sessions, 'current_session': current_session, 'active_model': get_model_status()})


@login_required
def session_list(request):
    sessions = ChatSession.objects.filter(user=request.user)
    return render(request, 'ai_assistant/partials/session_list.html', {'sessions': sessions})


@login_required
def session_detail(request, pk):
    session = get_object_or_404(ChatSession.objects.prefetch_related('messages'), pk=pk, user=request.user)
    sessions = ChatSession.objects.filter(user=request.user)
    return render(request, 'ai_assistant/chat.html', {'sessions': sessions, 'current_session': session, 'active_model': get_model_status()})


@login_required
def create_session(request):
    session = ChatSession.objects.create(user=request.user, title='Nova conversa')
    return redirect('ai_session_detail', pk=session.pk)


@login_required
def export_session_pdf(request, pk):
    session = get_object_or_404(ChatSession.objects.prefetch_related('messages'), pk=pk, user=request.user)
    lines = [session.title or 'Conversa', '=' * 40]
    for message in session.messages.all():
        lines.append(f'{message.get_role_display()}: {message.content}')
        lines.append('')
    response = HttpResponse(_simple_pdf_bytes(lines), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="chat-{session.pk}.pdf"'
    return response


@login_required
def chat_stream(request):
    message = request.GET.get('message', '').strip()
    if not message:
        raise Http404()

    session_id = request.GET.get('session_id')
    session = get_object_or_404(ChatSession, pk=session_id, user=request.user) if session_id else ChatSession.objects.create(user=request.user, title=message[:50])

    ChatMessage.objects.create(session=session, role='user', content=message)
    session.sync_title()

    def event_stream(prompt, user, chat_session):
        full_response = []
        try:
            agent = build_agent_for_user(user)
            for chunk in agent.stream({'input': prompt}):
                token = chunk.get('output')
                if token:
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token, 'session_id': chat_session.pk}, ensure_ascii=False)}\n\n"
            final_text = ''.join(full_response).strip()
        except Exception as exc:
            final_text = (
                'Não consegui responder agora. '
                'Verifique se o Ollama está rodando e se há um modelo disponível. '
                f'Detalhe técnico: {exc}'
            )
            yield f"data: {json.dumps({'token': final_text, 'session_id': chat_session.pk}, ensure_ascii=False)}\n\n"
        ChatMessage.objects.create(session=chat_session, role='assistant', content=final_text)
        AiAssistantLog.objects.create(user=user, prompt=prompt, response=final_text)
        yield f"data: {json.dumps({'done': True, 'session_id': chat_session.pk}, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(event_stream(message, request.user, session), content_type='text/event-stream')
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response


@login_required
def widget_context(request):
    sessions = ChatSession.objects.filter(user=request.user)[:6]
    model_status = get_model_status()
    return JsonResponse(
        {
            'sessions': [{'id': session.pk, 'title': session.title or 'Nova conversa'} for session in sessions],
            'model': model_status['model'],
            'status': model_status['status'],
        }
    )
