from rest_framework import viewsets, filters, views, status, response
from django_filters.rest_framework import DjangoFilterBackend
from pgvector.django import CosineDistance
from google import genai
import os
from .models import University, Programme
from .serializers import UniversitySerializer, ProgrammeSerializer, ProgrammeDetailSerializer

class UniversityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = University.objects.all().order_by('name')
    serializer_class = UniversitySerializer
    pagination_class = None
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'head_office', 'university_type']
    filterset_fields = ['head_office', 'university_type', 'status']

class ProgrammeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Programme.objects.all().select_related('university').order_by('name')
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'university__name', 'description']
    filterset_fields = ['award_level', 'study_mode', 'university']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            from .serializers import ProgrammeDetailSerializer
            return ProgrammeDetailSerializer
        return ProgrammeSerializer

class RecommendationView(views.APIView):
    def post(self, request):
        interests = request.data.get('interests', '')

        if not interests:
             return response.Response({"error": "Interests required"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             return response.Response({"error": "Server misconfigured (API Key)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client = genai.Client(api_key=api_key)
        
        try:
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=interests
            )
            user_embedding = result.embeddings[0].values
            
            matches = Programme.objects.order_by(CosineDistance('embedding', user_embedding))[:5]
            
            serializer = ProgrammeSerializer(matches, many=True)
            return response.Response(serializer.data)

        except Exception as e:
            return response.Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatView(views.APIView):
    def post(self, request):
        message = request.data.get('message', '')
        history = request.data.get('history', [])

        if not message:
            return response.Response({"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             return response.Response({"error": "Server misconfigured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client = genai.Client(api_key=api_key)

        try:
            embed_result = client.models.embed_content(
                model="text-embedding-004",
                contents=message
            )
            query_vector = embed_result.embeddings[0].values
            
            matches = Programme.objects.order_by(CosineDistance('embedding', query_vector))[:5]
            
            context_pieces = []
            for p in matches:
                info = f"- Programme: {p.name} at {p.university.name if p.university else 'Unknown University'}\n"
                info += f"  Award: {p.award_level}, Mode: {p.study_mode}\n"
                info += f"  Description: {p.description[:300]}..." 
                context_pieces.append(info)
            
            context_str = "\n".join(context_pieces)
            
            system_instruction = """You are the UniGuide AI Student Advisor, a helpful but neutral academic guide for Tanzanian universities.
            Your goal is to empower students to make their own informed decisions.

            GUIDELINES:
            1. **Be Neutral & Unbiased**: Do not favor one university over another unless the data explicitly supports a comparison requested by the student.
            2. **Encourage Exploration**: Never give a "final absolute answer" (e.g., "You must take this course"). Instead, say "You might consider X because..." or "This program aligns with your interests in Y." Always encourage the student to research further.
            3. **General Inquiries**: If a student asks a broad question (e.g., "What is the best engineering course?"), DO NOT limit your answer to just the specific universities in the context. Instead, provide a general overview of the field and suggest they look into various institutions.
            4. **Admit Unknowns**: If the provided Context does not contain the specific answer, explicitly state: "I don't have that specific information in my current database." Then, advise them to check official university prospectuses or websites.
            5. **Consultative Approach**: If a student asks "Which course should I take?" or similar broad questions, DO NOT immediately list courses. Instead, ask clarifying questions first (e.g., "What subjects do you enjoy?", "Do you prefer practical or theoretical work?", "What were your best subjects in high school?"). LISTEN to the student before recommending.
            6. **Be Useful**: Provide concrete details from the Context (durations, subjects, awards) when they are relevant and factual.

            INSTRUCTIONS:
            - Answer based on the provided Context and your general academic knowledge.
            - Format your response nicely with markdown (bullet points, bold text).
            """
            
            full_prompt = f"{system_instruction}\n\nCONTEXT FROM DATABASE:\n{context_str}\n\nSTUDENT QUESTION:\n{message}"
            
            chat_session = client.chats.create(model='gemini-2.0-flash')
            response_obj = chat_session.send_message(full_prompt)
            
            return response.Response({
                "response": response_obj.text,
                "context_used": [p.name for p in matches] 
            })

        except Exception as e:
            return response.Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
