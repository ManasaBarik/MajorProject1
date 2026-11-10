from rest_framework.views import APIView
from rest_framework import generics, serializers as rs
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.db import transaction
from drf_spectacular.utils import extend_schema
from common.responses import success
from common.schemas import APIEnvelopeSerializer, ChatRequestSerializer
from .models import FAQ, Conversation, Message


SUPPORTED_LANGUAGES = {"en", "hi", "od"}
SUPPORTED_CONTEXTS = {"CITIZEN", "BUSINESS"}


_OFFICIAL_INTRO = (
    "Based on official municipal information (please consult the relevant department for the final decision): "
)
_GENERAL_INTRO = "General guidance (verify with the relevant authority): "


def _official_sources(faqs=None, docs=None):
    result = []
    if faqs:
        for f in faqs:
            result.append({"title": f.question[:120], "type": "official"})
    if docs:
        for d in docs:
            result.append({"title": d.title[:120], "type": "official"})
    return result


class ConversationListSerializer(rs.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "title", "context", "language", "created_at", "updated_at")
        read_only_fields = fields


class MessageSerializer(rs.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "sender", "content", "language", "sources", "created_at")
        read_only_fields = fields


class ConversationDetailSerializer(rs.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "context", "language", "created_at", "updated_at", "messages")
        read_only_fields = fields


class ChatView(APIView):
    @extend_schema(request=ChatRequestSerializer, responses=APIEnvelopeSerializer)
    @transaction.atomic
    def post(self, request):
        msg = (request.data.get("message") or "").strip()
        lang = (request.data.get("language") or "en").strip()
        context = (request.data.get("context") or "CITIZEN").strip()
        conversation_id = request.data.get("conversation_id")

        if lang not in SUPPORTED_LANGUAGES:
            raise ValidationError({"language": f"Supported languages are {sorted(SUPPORTED_LANGUAGES)}."})
        if not msg:
            raise ValidationError({"message": "Message is required."})
        if context not in SUPPORTED_CONTEXTS:
            raise ValidationError({"context": f"Supported contexts are {sorted(SUPPORTED_CONTEXTS)}."})

        faqs = list(FAQ.objects.filter(active=True))
        matched_faqs = []
        for faq in faqs:
            q = faq.question.lower()
            needle = msg.lower()[:40]
            if needle and (needle in q or any(tok in q for tok in msg.lower().split() if len(tok) > 3)):
                matched_faqs.append(faq)
                if len(matched_faqs) >= 3:
                    break

        if matched_faqs:
            answer = _OFFICIAL_INTRO + " ".join(f.answer for f in matched_faqs[:2])
            sources = _official_sources(faqs=matched_faqs[:3])
        else:
            answer = "The intelligent chatbot service is not configured yet. Please contact the relevant municipal department for assistance."
            sources = []

        user = request.user
        conv = None
        if conversation_id:
            try:
                conv = Conversation.objects.get(id=conversation_id, user=user)
            except Conversation.DoesNotExist:
                pass
        if conv is None:
            conv = Conversation.objects.create(
                user=user,
                title=msg[:60],
                context=context,
                language=lang,
            )
        else:
            conv.language = lang
            conv.context = context
            conv.save(update_fields=["language", "context", "updated_at"])

        Message.objects.create(conversation=conv, sender="USER", content=msg, language=lang)
        bot_msg = Message.objects.create(
            conversation=conv,
            sender="BOT",
            content=answer,
            language=lang,
            sources=sources,
        )

        return success({
            "message": answer,
            "language": lang,
            "sources": sources,
            "conversation_id": conv.id,
        })


class ConversationsListView(generics.ListAPIView):
    serializer_class = ConversationListSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversation.objects.none()
        return Conversation.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_queryset(), many=True).data)


class ConversationDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationDetailSerializer
    queryset = Conversation.objects.all()

    def get_object(self):
        obj = super().get_object()
        if obj.user_id != self.request.user.id:
            raise NotFound()
        return obj

    def get(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)
