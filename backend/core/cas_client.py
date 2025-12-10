import httpx
import xmltodict
from urllib.parse import urlencode

class CASClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')

    def get_login_url(self, service_url: str) -> str:
        """
        Generate the CAS login URL with the service parameter.
        """
        params = {'service': service_url}
        return f"{self.server_url}/login?{urlencode(params)}"

    def get_logout_url(self, service_url: str = None) -> str:
        """
        Generate the CAS logout URL.
        """
        url = f"{self.server_url}/logout"
        if service_url:
            params = {'service': service_url}
            url += f"?{urlencode(params)}"
        return url

    async def validate_ticket(self, ticket: str, service_url: str) -> dict:
        """
        Validate the generic Service Ticket (ST) against the CAS server.
        Uses /serviceValidate (CAS 2.0).
        Returns user attributes if valid, else None.
        """
        validate_url = f"{self.server_url}/serviceValidate"
        params = {
            'service': service_url,
            'ticket': ticket
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Disable SSL verification for testing if needed, but best to keep verify=True in prod
                # Usage: verify=False if self-signed certs (common in dev/staging)
                response = await client.get(validate_url, params=params, timeout=10.0)
                if response.status_code != 200:
                    print(f"CAS Validation Failed: HTTP {response.status_code}")
                    return None
                
                # Parse XML response
                data = xmltodict.parse(response.content)
                service_response = data.get('cas:serviceResponse', {})
                
                if 'cas:authenticationSuccess' in service_response:
                    success = service_response['cas:authenticationSuccess']
                    user = success.get('cas:user')
                    attributes = success.get('cas:attributes', {})
                    
                    return {
                        'user': user,
                        'attributes': attributes
                    }
                else:
                    failure = service_response.get('cas:authenticationFailure', {})
                    print(f"CAS Auth Failure: {failure}")
                    return None
                    
            except Exception as e:
                print(f"CAS Validation Error: {str(e)}")
                return None
