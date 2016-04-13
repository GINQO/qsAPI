# -*- coding: UTF-8 -*-


#import ConfigParser
import sys, os.path
from distutils.version import LooseVersion as Version
import requests as req
from urllib.parse import urlencode, urljoin
import random, string


class Verbose(object):
        ''' Verbosity enumeration '''
        (MINIMAL, API, INFO, DEBUG)=_levels=range(4)
        
        
        def __init__(self, value=None):
            if not self.set(value):
                self.verbosity=self.MINIMAL
                
        def set(self, value):
            if value:
                val=int(value)
                if val in self._levels:
                    self.verbosity=val
                    if val < self.DEBUG:
                        sys.tracebacklimit = 0
                    return True
            return False
        
        def get(self):
            return self.verbosity
        
        def isMinimal(self):
            return self.verbosity >= self.MINIMAL
        
        def isApi(self):
            return self.verbosity >= self.API
        
        def isInfo(self):
            return self.verbosity >= self.INFO
        
        def isDebug(self):
            return self.verbosity >= self.DEBUG


    


class _Controller(object):
    """ Handler REST-API QRS"""
       
    _referer='python APIREST (QlikSense)' 
    
    def __init__(self, proxy, port, vproxy, certificate, verify, verbosity):
        ''' 
            @Function setup: Setup the connection and initialize handlers
            @param proxy: hostname to connect
            @param port: port number
            @param certificate: path to .pem client certificate
            @param verify: false to trusth in self-signed certificates
            @param verbosity: debug level
        '''
        self.baseurl  = None
        self.request  = None
        self.response = None
        self.session  = None
        self.verbose  = Verbose()
        self.UserDirectory='Internal'
        self.UserId = 'sa_repository'
          
        self.verbose.set(verbosity)
        
        self.baseurl= 'https://{host}:{port}'.format(host=proxy, port=str(port))
        self.vproxy= vproxy.strip('/')
        self.preffix=self.vproxy+'/' if vproxy else '' 
        
        if isinstance(certificate, str):
            (base,ext)=os.path.splitext(certificate)
            self.cafile=(base+ext, base+'_key'+ext)
            if self.verbose.isDebug():
                print(' CERTKEY: {0}{1}'.format(base, ext))
        else:
            self.cafile=certificate
            if self.verbose.isDebug():
                print(' CERT: {0}'.format(certificate))
        self._verify=bool(verify)
        
        if not self._verify:
            req.packages.urllib3.disable_warnings()
                
        self.session=req.Session()
        

        
    def _params_prepare(self, param, xhd={}):
                
        par=dict({'Xrfkey': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))})

        if isinstance(param, dict):
            for p,v in param.items():
                if v is not None:
                    if isinstance(v, bool):
                        par[p]=str(v).lower()
                    else:
                        par[p]=str(v)
                    if self.verbose.isInfo():
                        print("\t{par}=>{val}".format(par=p, val=par[p]))
                else:
                    if self.verbose.isInfo():
                        print("\t{par}=>(default)".format(par=p))
            
        
        hd= { 'User-agent': self._referer,
              'Pragma': 'no-cache',
              'X-Qlik-User': 'UserDirectory={directory}; UserId={user}'.format(directory=self.UserDirectory, user=self.UserId),
              'X-Qlik-Virtual-Proxy-Prefix:': self.vproxy,
              'x-Qlik-Xrfkey': par.get('Xrfkey'),
              'Accept': 'application/json',
              'Content-Type': 'application/json'}
        
        hd.update(xhd)
        
        return(par, hd)  
    
       
    def call(self, method='GET', apipath='/', param=None, data=None, files=None):
        """ initialize control structure """
               
        if str(method).upper() not in ('GET', 'POST', 'PUT', 'DELETE'):
            raise Exception('invalid method <{0}>'.format(method))
       
        if self.verbose.isInfo():
            print('\n API endpoint <{0}>'.format(apipath))
        
        (par,hd)=self._params_prepare(param, {} if files is None else {'Content-Type': 'application/vnd.qlik.sense.app'})
        
        # Build the request        
        self.response= None
        url='{0}/{1}?{2}'.format(self.baseurl, apipath.lstrip('/'), urlencode(par))
        self.request=req.Request(method, url, headers=hd, data=data, files=files)
        pr=self.request.prepare()
                
        if self.verbose.isInfo():
            print('\tSEND: '+url)
                
        # Execute the HTTP request 
        try:
            self.response = self.session.send(pr, cert=self.cafile, verify=self._verify)
                
            if self.verbose.isInfo():
                if len(self.response.text) < 120 or self.verbose.isDebug():
                    print('\tRECV: '+self.response.text)
                else:
                    print('\tRECV: '+self.response.text[:60]+' <<<  >>> '+self.response.text[-60:])
            
        except ValueError as e:
            raise Exception('<Value error> {0}'.format(e))
        except IOError as e:
            raise Exception('<IO error> {0}'.format(e))
        except Exception as e:
            raise Exception('<Unknow error> {0}'.format(e))
        
        return(self.response)



    def download(self, apipath, filename, param=None):
        """ initialize control structure """
        
        chunk_size=512     
                       
        if self.verbose.isInfo():
            print('\n API endpoint <{0}>'.format(apipath))

        (par,hd)=self._params_prepare(param)
        
        
        # Build the request        
        self.response= None
        url='{0}/{1}?{2}'.format(self.baseurl, apipath.lstrip('/'), urlencode(par))
     
        
        if self.verbose.isInfo():
            print('\tSEND: '+url)

                
        # Execute the HTTP request 
        try:
            self.request = req.get(url, headers=hd, cert=self.cafile, verify=self._verify, stream=True)
                
            with open(filename, 'wb') as f:
                if self.verbose.isInfo():
                    print('\tDOWN({0}Kb block): '.format(str(chunk_size)), end='',flush=True)
                
                #download in 512Kb blocks
                for chunk in self.request.iter_content(chunk_size=chunk_size*1024): 
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        if self.verbose.isInfo():
                            print('.', end='',flush=True)
                            
                if self.verbose.isInfo():
                    print('Done.')
                    print('\tSaved: {0}'.format(os.path.abspath(filename)))
                
            
        except ValueError as e:
            raise Exception('<Value error> {0}'.format(e))
        except IOError as e:
            raise Exception('<IO error> {0}'.format(e))
        except Exception as e:
            raise Exception('<Unknow error> {0}'.format(e))
        
        return(self.request.ok)

    
    #TODO: crear un upload
    def upload(self, apipath, filename, param=None):
        """ initialize control structure """
        
        chunk_size=512     
                       
        if self.verbose.isInfo():
            print('\n API endpoint <{0}>'.format(apipath))

        (par,hd)=self._params_prepare(param, {'Content-Type': 'application/vnd.qlik.sense.app'})
        
        
        # Build the request        
        self.response= None
        url='{0}/{1}?{2}'.format(self.baseurl, apipath.lstrip('/'), urlencode(par))
     
        
        if self.verbose.isInfo():
            print('\tSEND: '+url)

                
        # Execute the HTTP request 
        try:
            
            with open(filename, 'rb') as f:
                if self.verbose.isInfo():
                    print('\tUP({0}Kb block): '.format(str(chunk_size)), end='',flush=True)
                
                #upload
                self.request = req.post(url, headers=hd, cert=self.cafile, verify=self._verify, data=f, stream=True)
                
                if self.verbose.isInfo():
                    print('Done.')                
            
        except ValueError as e:
            raise Exception('<Value error> {0}'.format(e))
        except IOError as e:
            raise Exception('<IO error> {0}'.format(e))
        except Exception as e:
            raise Exception('<Unknow error> {0}'.format(e))
        
        return(self.request.ok)


    
    
    def get(self, apipath='/qrs/about/api/description', param=None):
        '''
        @Function get: generic purpose call
        @param apipath: uri REST path
        @param param : whatever other param needed in form a dict
                      (example: {'filter': "name eq 'myApp'} )
        '''
        return self.call('GET', apipath, param)
    
    
    
    def post(self, apipath, param=None, data=None, files=None):
        '''
        @Function post: generic purpose call
        @param apipath: uri REST path
        @param param : whatever other param needed in form a dict
                      (example: {'filter': "name eq 'myApp'} )
        @param data : stream data input
        @param files : metafile input 
        '''
        return self.call('POST', apipath, param, data, files)
    
    
    
    def put(self, apipath, param=None, data=None):
        '''
        @Function put: generic purpose call
        @param apipath: uri REST path
        @param param : whatever other param needed in form a dict
                      (example: {'filter': "name eq 'myApp'} )
        @param data : stream data input
        @param files : metafile input
        '''
        return self.call('PUT', apipath, param, data)
    
    
    
    def delete(self, apipath, **params):
        '''
        @Function delete: generic purpose call
        @param apipath: uri REST path
        @param param : whatever other param needed in form a dict
                      (example: {'filter': "name eq 'myApp'} )
        '''
        return self.call('DELETE', apipath, **params)

    
    

class QPS(object):
    '''Qlik Sense Proxy Service REST API'''
    
    VERSION_API= Version('2.1.0')
    
    
    def __init__(self, proxy='localhost', port=4243, vproxy='', certificate=None, verify=False, verbosity=Verbose.INFO):  
        
        self.driver=_Controller(proxy, port, vproxy, certificate, verify, verbosity)



    def GetUser(self, directory, user):
        '''
        @Function: This returns all proxy sessions that a user (identified by {directory} and {user}) has.
        '''
        apipath='/qps/{virtual_proxy}user/{directory}/{id}'.format(virtual_proxy=self.driver.preffix, directory=directory, id=user)
        return self.driver.get(apipath)
    
    
    def DeleteUser(self, directory, user):
        '''
        @Function: This is part of the Logout API. The directory and ID are the same UserDirectory and UserId as those that were sent in POST /qps/{virtual proxy/}ticket.
                    A list of all proxy sessions that were connected to the deleted user is returned. 
        '''
        apipath='/qps/{virtual_proxy}user/{directory}/{id}'.format(virtual_proxy=self.driver.preffix, directory=directory, id=user)
        return self.driver.delete(apipath)
    
    
    def GetSession(self, pId):
        '''
        @Function: This returns the proxy session identified by {id}.
        '''
        apipath='/qps/{virtual_proxy}session/{id}'.format(virtual_proxy=self.driver.preffix, id=pId)
        return self.driver.get(apipath)




class QRS(object):
    '''Qlik Sense Repository Service REST API'''
    
    VERSION_API= Version('2.1.0')
    
    
    def __init__(self, proxy='localhost', port=4242, vproxy='', certificate=None, verify=False, verbosity=Verbose.INFO):
        
        self.driver=_Controller(proxy, port, vproxy, certificate, verify, verbosity)
        self.VERSION_SERVER=self.getServerVersion()
        if self.VERSION_API > self.VERSION_SERVER:
            raise Exception('<server version mismatch, API:{0} > Server:{1}'.format(self.VERSION_API, self.VERSION_SERVER))
        else:
            if self.driver.verbose.isApi():
                print(' Server version: {0}'.format(self.VERSION_SERVER))



    def ping(self):
        '''
        @return: “Ping successful”, if there are no problems contacting the Qlik Sense Repository Service (QRS).
        '''
        return self.driver.call('GET', '/ssl/ping')



        
    def getServerVersion(self):
        '''
        @Function: retrieve the server version
        '''
        return Version(self.driver.call('GET', '/qrs/about').json().get('buildVersion'))

 
 
    
    def getAbout(self):
        '''
        @Function getAbout: Get information on the Qlik Sense repository, including version, database provider, and whether the node is the central node of the site or not.
        '''
        return self.driver.get('/qrs/about')
    
 
    
    def count(self, pType, pFilter=None):
        '''
        @Function count: generic purpose call
        @param pType: entity to count
        @param pFilter: filter the entities before calculating the number of entities. 
        @return : integer from json response
        '''
        return self.driver.get('/qrs/{0}/count'.format(pType), param={'filter':pFilter}).json()['value']
 
    
    
    def getDescription(self, extended='False', method=None, outformat='JSON'):
        '''@Function getDescription: List all paths available in the Qlik Sense Repository Service (QRS) API. Optionally, return extended information, endpoints that use a specific HTTP verb, or the return values in JSON format.
           @param extended: If true, returns the following:
                The type (if any) that needs to be included in the body.
                The type of return value (if any).
                If the endpoint is automatically generated or not.
           @param method:  If set to an HTTP verb (GET, PUT, POST, or DELETE), only endpoints that use the verb are returned.
           @param outformat:  If set to "JSON", the return value is given in JSON format. 
        '''
            
        param={'extended': extended in ('True', 'true', True),
               'method'  : method,
               'format'  : outformat}
        
        return self.driver.get('/qrs/about/api/description', param).json()



    def getEnum(self):
        '''@Function getEnum: Get all enums that are used by the public part of the Qlik Sense Repository Service (QRS) API.
        '''
        return self.driver.get('/qrs/about/api/enums').json()

    
    
    def AppDictAttributes(self, guid=None, key='id', attr='name'):
        '''@Function: retrieve a mapping of apps attributes
           @param pId: limmit the scope to the App {GUID}
           @param key: the attribute to be the key
           @param attr: the attribute value to retrieve
           @return: dict(key:attr)
        '''
        
        apipath=urljoin('/qrs/app/', guid) if guid else '/qrs/app/full'
            
        s=self.driver.get(apipath)
        r={}
        if s.ok:
            j=s.json()
            if guid:
                r[j.get(key)]=j.get(attr)
            else:
                for x in j:
                    r[x.get(key)]=x.get(attr)
        
        return(r)
    
    
    
    def AppCopy(self, pId, name=None):
        '''
        @Function: Copy an existing app, identified by {id}. Optionally, provide a name for the copy.
        @param pId: app identifier
        @param name: Name of the app
        '''
        param={'name':name}
        return self.driver.post('/qrs/app/{id}/copy'.format(id=pId), param).json()

    
    
    
    def AppExport(self, pId, filename=None):
        '''
        @Function: Get an export qvf for an existing app, identified by {id}.
        @param pId: app GUI
        @param filename: target path filename
        '''
        
        r=self.driver.get('/qrs/app/{id}/export'.format(id=pId))
        if r.ok:
            file= (filename.rstrip('.qvf') if filename else pId)+'.qvf'
            r=self.driver.download('/qrs/download/app/{appId}/{TicketId}/{fileName}'.format(appId=pId, TicketId=r.json()['value'], fileName=file), file)
        return(r)
    
    
    
    #TODO: VERIFICAR
    #TODO: cambios con 2.2
    def AppUpload(self, filename, name):
        '''
        @Function: Upload a filename.qvf into Central Node.
        @param filename: target path filename
        @param name: target app name
        '''
        param ={'name':name}
        return(self.driver.upload('/qrs/app/upload', filename, param))
    
    

    #TODO: VERIFICAR    
    def SystemRules(self, pFilter=None):
        '''
        @Function: Get the system rules
        '''
        return(self.driver.driver.get('/qrs/systemrule/full', {'filter':pFilter}))
    




if __name__ == "__main__":
    
    from pprint import pprint
    
    e=QRS(proxy='52.29.108.33', verbosity=Verbose.DEBUG, certificate='C:\\Users\\Test\\workspace\\QSenseAPI\\ec2\\client.pem')
    e.ping()
    
    pprint(e.AppDict())
    pprint([e.count(x) for x in ('app','user','stream','dataconnection')])


    