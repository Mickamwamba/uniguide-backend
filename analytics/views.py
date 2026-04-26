from rest_framework import views, response, status
from .models import SearchLog, GuidanceSessionLog, PageViewLog, EligibilityCheckLog

class TelemetryTrackingView(views.APIView):
    """
    A single robust endpoint that accepts telemetry POST requests from the react application
    without imposing heavy blocking validation bottlenecks.
    """
    authentication_classes = [] 
    permission_classes = []
    
    def post(self, request):
        event_type = request.data.get('event_type')
        payload = request.data.get('payload', {})
        
        session_id = payload.get('session_id')
        
        # Early exit if missing requirements
        if not event_type or not session_id:
            return response.Response({"status": "ignored", "reason": "missing meta"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if event_type == 'search':
                SearchLog.objects.create(
                    session_id=session_id,
                    query_string=payload.get('query', ''),
                    filters_applied=payload.get('filters', {}),
                    results_count=payload.get('results_count', 0),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            
            elif event_type == 'guidance_conversion':
                # If they are actively generating new recommendations, we MUST create a brand new log instance.
                # If they are just capturing their email (lead conversion), we update the most recent instance.
                if 'ai_recommendations' in payload:
                    GuidanceSessionLog.objects.create(
                        session_id=session_id,
                        pathway=payload.get('pathway', ''),
                        academic_inputs=payload.get('academic_inputs', {}),
                        psychometric_inputs=payload.get('psychometric_inputs', {}),
                        ai_recommendations=payload.get('ai_recommendations', []),
                        ai_synthesis=payload.get('ai_synthesis', ''),
                        converted_to_lead=payload.get('converted_to_lead', False),
                        ip_address=self._get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                else:
                    # Funnel progression: Update the most recent log in this session
                    log = GuidanceSessionLog.objects.filter(session_id=session_id).order_by('-created_at').first()
                    if log:
                        if 'converted_to_lead' in payload: 
                            log.converted_to_lead = payload['converted_to_lead']
                        log.save()
                
            elif event_type == 'page_view':
                PageViewLog.objects.create(
                    session_id=session_id,
                    entity_type=payload.get('entity_type', 'PROGRAMME'),
                    entity_id=payload.get('entity_id'),
                    referrer=payload.get('referrer', ''),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
            elif event_type == 'eligibility_check':
                EligibilityCheckLog.objects.create(
                    session_id=session_id,
                    programme_id=payload.get('programme_id'),
                    academic_inputs=payload.get('academic_inputs', {}),
                    ai_decision=payload.get('ai_decision', False),
                    failure_reason=payload.get('failure_reason', ''),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
        except Exception as e:
             # Failsafe: tracking should never crash the user's primary experience
             print(f"[Telemetry Error] -> {e}")
             return response.Response({"status": "failed"}, status=status.HTTP_200_OK)

        return response.Response({"status": "tracked"}, status=status.HTTP_200_OK)
        
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
