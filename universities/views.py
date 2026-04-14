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
        combination = request.data.get('combination', '')
        personality = request.data.get('personality', {})
        if not interests and not combination:
             return response.Response({"error": "Profile data required"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             return response.Response({"error": "Server misconfigured (API Key)"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client = genai.Client(api_key=api_key)
        
        try:
            import json
            
            # Phase 1: Agentic Synthesis (JSON Structured)
            prompt = f"""
            You are an expert Tanzanian University Admissions Advisor.
            A high school student has submitted their profile. Your task is to evaluate them and return a JSON object with EXACTLY two keys:
            1. "search_string": A highly dense 100-word paragraph describing exact university degrees and career titles checking for their precise subject alignment and aspirations. This string is purely for our internal semantic vector database search.
            2. "user_summary": A friendly, neutral, and empowering 3-4 sentence paragraph speaking directly to the student. Focus entirely on their personality and interests. Include 1 or 2 statements highlighting exciting potential career futures they could explore based on their profile. Be modest, encouraging, and empower them to discover their own paths. (e.g. "Your passion for [X] opens up possibilities to explore careers like [Y] or [Z]. The pathways below might inspire your journey...")
            
            Student Profile:
            - A-Level Combination: {combination}
            - Stated Interests: {interests}
            
            Psychological Traits:
            - Ideal Work Environment: {personality.get('environment', 'Not stated')}
            - Preferred Activity: {personality.get('activity', 'Not stated')}
            - Societal Impact: {personality.get('impact', 'Not stated')}
            - Natural Role: {personality.get('role', 'Not stated')}
            
            CRITICAL Context:
            - Focus entirely on parsing their combination and psychological traits to align them with perfect careers. Do not mention grades.
            
            Respond strictly in valid JSON format. Do not use markdown backticks around the json.
            """
            
            synthesis_response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            raw_text = synthesis_response.text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
                
            try:
                parsed_synthesis = json.loads(raw_text.strip())
                search_string = parsed_synthesis.get("search_string", raw_text)
                user_summary = parsed_synthesis.get("user_summary", raw_text)
            except json.JSONDecodeError:
                search_string = raw_text
                user_summary = "Based on your academic profile and interests, here are the exact degree pathways we found perfectly suited for you!"
            
            # Phase 2: Vector Generation
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=search_string
            )
            user_embedding = result.embeddings[0].values
            
            # Phase 3: Semantic Search + Hard Constraints
            from difflib import SequenceMatcher
            
            # Formally exclude postgraduate programs
            base_query = Programme.objects.exclude(
                award_level__icontains="Master"
            ).exclude(
                award_level__icontains="PhD"
            ).exclude(
                award_level__icontains="Doctor"
            ).exclude(
                award_level__icontains="Postgraduate"
            )
            
            # Pull top 150 broad matches across all Bachelor/Diploma levels to ensure deep clustering netting
            matches = base_query.order_by(CosineDistance('embedding', user_embedding))[:150]

            def is_similar(a, b):
                # Clean filler words
                replaces = [("bachelor of science in ", ""), ("bachelor of arts in ", ""), 
                            ("bachelor of ", ""), ("bsc in ", ""), ("ba in ", ""), 
                            ("bsc ", ""), ("ba ", ""), ("b.sc ", ""), ("b.a ", "")]
                clean_a, clean_b = a.lower(), b.lower()
                for r, txt in replaces:
                    clean_a = clean_a.replace(r, txt)
                    clean_b = clean_b.replace(r, txt)
                clean_a, clean_b = clean_a.strip(), clean_b.strip()
                
                if clean_a == clean_b: return True
                if clean_a in clean_b or clean_b in clean_a: return True
                
                # Check word intersection threshold
                words_a, words_b = set(clean_a.split()), set(clean_b.split())
                if len(words_a) > 0 and len(words_b) > 0:
                    shorter = min(len(words_a), len(words_b))
                    # If 80%+ of words match regardless of order
                    if len(words_a.intersection(words_b)) / shorter >= 0.8:
                        return True
                        
                return SequenceMatcher(None, clean_a, clean_b).ratio() > 0.75

            clusters = []
            clustered_ids = set()

            for i, p1 in enumerate(matches):
                prog1_id = str(p1.id)
                if prog1_id in clustered_ids:
                    continue
                
                # Create a new Generic Programme Cluster
                current_cluster = {
                    "generic_name": p1.name,   
                    "general_description": p1.description,
                    "award_level": p1.award_level,
                    "offered_at": [
                        {
                            "id": prog1_id,
                            "university_name": p1.university.name if p1.university else "Unknown",
                            "duration": getattr(p1, 'duration_months', None)
                        }
                    ]
                }
                clustered_ids.add(prog1_id)
                
                # Scan remaining matches to group similar degrees
                for p2 in matches[i+1:]:
                    prog2_id = str(p2.id)
                    if prog2_id not in clustered_ids and is_similar(p1.name, p2.name):
                        # Avoid adding the same university twice in the same generic cluster 
                        existing_unis = [u['university_name'] for u in current_cluster['offered_at']]
                        uni_name = p2.university.name if p2.university else "Unknown"
                        if uni_name not in existing_unis:
                            current_cluster['offered_at'].append({
                                "id": prog2_id,
                                "university_name": uni_name,
                                "duration": getattr(p2, 'duration_months', None)
                            })
                            clustered_ids.add(prog2_id)
                
                clusters.append(current_cluster)
            
            # Sort explicitly: Bachelor degrees strictly above Diplomas
            def get_award_rank(level):
                level_str = (level or "").lower()
                if 'bachelor' in level_str or 'degree' in level_str:
                    return 1
                if 'diploma' in level_str:
                    return 2
                if 'certificate' in level_str:
                    return 3
                return 4
                
            clusters.sort(key=lambda c: get_award_rank(c.get('award_level')))
            
            # Slice top 6 distinct generic degree clusters
            final_clusters = clusters[:6]

            return response.Response({
                "matches": final_clusters,
                "ai_synthesis": user_summary
            })

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
                model="gemini-embedding-001",
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
            
            system_instruction = """You are the Pathfinder AI Student Advisor, a highly intelligent and engaging academic guide for Tanzanian universities.
            Your goal is to empower students to make informed decisions, prioritizing bachelor degrees by default unless they specify otherwise.

            GUIDELINES:
            1. **Be Immediately Useful**: Provide valuable, high-level insights into career fields right away. Generalize their interests to explain WHAT a field entails before diving into specific programs.
            2. **Don't Over-Interrogate**: NEVER bombard the student with a list of questions. If their request is broad, give a thoughtful generalized breakdown of potential pathways, and optionally end with ONE soft clarifying question.
            3. **Strict Progressive Disclosure**: ABSOLUTELY DO NOT mention specific university names (like UDSM, OUT, UDOM) or exact degree titles from the Context prematurely. Discuss general academic landscapes, fields of study, and career paths first. ONLY list specific university programs if the student explicitly commands you to (e.g. "Which universities offer this?").
            4. **Be Neutral & Unbiased**: Never inject institutional bias.
            5. **Admit Unknowns**: If the provided Context lacks specific admission details, advise them to check official university prospectuses.
            6. **Be Concrete Later**: When they finally do ask for specific courses, only then provide concrete details from the Context (universities, durations, awards).

            INSTRUCTIONS:
            - Answer based on the provided Context and your general academic knowledge.
            - Before answering anything make sure you fully understand what the student is asking. NEVER list specific courses or universities from the context unless the student explicitly asks for them.
            - Keep your responses structured, insightful, and warmly conversational.
            - Format your response beautifully with markdown (bullet points, bold text).
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
