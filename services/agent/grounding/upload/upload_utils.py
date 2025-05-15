class Resource:
    """Base class for all resources attached to a user message."""
    
    def __init__(self, content: Union[str, bytes, BinaryIO], 
                 content_type: Optional[str] = None,
                 filename: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        
        # Handle content based on type
        if isinstance(content, str) and os.path.isfile(content):
            # If content is a file path
            self.filename = os.path.basename(content) if filename is None else filename
            with open(content, 'rb') as f:
                self.content = f.read()
            self.content_type = content_type or mimetypes.guess_type(content)[0] or 'application/octet-stream'
        elif hasattr(content, 'read'):
            # If content is a file-like object
            self.content = content.read()
            self.filename = filename or getattr(content, 'name', f"file-{self.id}")
            self.content_type = content_type or mimetypes.guess_type(self.filename)[0] or 'application/octet-stream'
        else:
            # Direct content (string or bytes)
            self.content = content
            self.filename = filename or f"resource-{self.id}"
            self.content_type = content_type or 'text/plain' if isinstance(content, str) else 'application/octet-stream'
    
    def get_size(self) -> int:
        """Return the size of the content in bytes."""
        if isinstance(self.content, str):
            return len(self.content.encode('utf-8'))
        return len(self.content)
    
    def __repr__(self) -> str:
        return f"<Resource id={self.id} type={self.content_type} filename={self.filename}>"


class TextResource(Resource):
    """Text-based resource."""
    
    def __init__(self, content: str, filename: Optional[str] = None):
        super().__init__(content, 'text/plain', filename)
        
    def get_text(self) -> str:
        """Return the text content."""
        if isinstance(self.content, bytes):
            return self.content.decode('utf-8')
        return self.content


class DocumentResource(Resource):
    """Document resource (PDF, DOCX, etc.)."""
    
    def __init__(self, content: Union[str, bytes, BinaryIO], 
                 content_type: Optional[str] = None,
                 filename: Optional[str] = None):
        super().__init__(content, content_type, filename)
        
    def get_mime_category(self) -> str:
        """Return the general category of the document."""
        main_type = self.content_type.split('/')[0] if self.content_type else 'unknown'
        sub_type = self.content_type.split('/')[1] if '/' in self.content_type else ''
        
        if main_type == 'application':
            if any(x in sub_type for x in ['pdf', 'document', 'msword', 'wordprocessing']):
                return 'document'
            elif any(x in sub_type for x in ['spreadsheet', 'excel', 'xls']):
                return 'spreadsheet'
            elif any(x in sub_type for x in ['presentation', 'powerpoint', 'ppt']):
                return 'presentation'
        
        return main_type


class ImageResource(Resource):
    """Image resource."""
    
    def __init__(self, content: Union[str, bytes, BinaryIO], 
                 content_type: Optional[str] = None,
                 filename: Optional[str] = None):
        super().__init__(content, content_type, filename)
        
        # Ensure content type is an image type
        if not self.content_type.startswith('image/'):
            self.content_type = 'image/' + (self.content_type if self.content_type else 'jpeg')


class AudioResource(Resource):
    """Audio resource."""
    
    def __init__(self, content: Union[str, bytes, BinaryIO], 
                 content_type: Optional[str] = None,
                 filename: Optional[str] = None,
                 duration_seconds: Optional[float] = None):
        super().__init__(content, content_type, filename)
        
        # Ensure content type is an audio type
        if not self.content_type.startswith('audio/'):
            self.content_type = 'audio/' + (self.content_type if self.content_type else 'mp3')
            
        self.duration_seconds = duration_seconds


class LinkResource(Resource):
    """Web link resource."""
    
    def __init__(self, url: str, title: Optional[str] = None):
        super().__init__(url, 'text/uri-list', title or url)
        self.url = url
        self.title = title or url


class UserMessage:
    """
    Class representing a user message to an AI chatbot.
    Can contain text, audio, and various resources like documents and images.
    """
    
    def __init__(self, 
                 text: Optional[str] = None,
                 audio: Optional[Union[str, bytes, BinaryIO, AudioResource]] = None,
                 resources: Optional[List[Resource]] = None,
                 metadata: Optional[Dict] = None):
        """
        Initialize a user message.
        
        Args:
            text: Plain text content of the message
            audio: Audio content as AudioResource, path, bytes, or file-like object
            resources: List of resources attached to the message
            user_id: Identifier for the user
            conversation_id: Identifier for the conversation
            metadata: Additional metadata for the message
        """
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.text = text or ""
        self.resources = resources or []
        self.metadata = metadata or {}
        
        # Process audio if provided
        if audio:
            if isinstance(audio, AudioResource):
                self.audio = audio
            else:
                self.audio = AudioResource(audio)
            self.has_audio = True
        else:
            self.audio = None
            self.has_audio = False
    
    def add_resource(self, resource: Union[Resource, str, bytes, BinaryIO],
                   content_type: Optional[str] = None) -> Resource:
        """
        Add a resource to the message.
        
        Args:
            resource: The resource to add (can be a Resource object, file path, binary content, or file-like object)
            content_type: Content type of the resource (used if resource is not a Resource object)
            
        Returns:
            The added resource
        """
        if not isinstance(resource, Resource):
            # Determine resource type based on content_type
            if content_type:
                main_type = content_type.split('/')[0]
                if main_type == 'image':
                    resource = ImageResource(resource, content_type)
                elif main_type == 'audio':
                    resource = AudioResource(resource, content_type)
                elif main_type == 'text' and content_type != 'text/uri-list':
                    resource = TextResource(resource if isinstance(resource, str) else resource.decode('utf-8'))
                else:
                    resource = DocumentResource(resource, content_type)
            else:
                # Try to guess based on content
                if isinstance(resource, str):
                    if resource.startswith(('http://', 'https://')):
                        resource = LinkResource(resource)
                    elif os.path.isfile(resource):
                        mime_type = mimetypes.guess_type(resource)[0]
                        if mime_type:
                            main_type = mime_type.split('/')[0]
                            if main_type == 'image':
                                resource = ImageResource(resource, mime_type)
                            elif main_type == 'audio':
                                resource = AudioResource(resource, mime_type)
                            elif main_type == 'text':
                                with open(resource, 'r') as f:
                                    resource = TextResource(f.read(), os.path.basename(resource))
                            else:
                                resource = DocumentResource(resource, mime_type)
                        else:
                            resource = DocumentResource(resource)
                    else:
                        resource = TextResource(resource)
                else:
                    resource = DocumentResource(resource, content_type)
        
        self.resources.append(resource)
        return resource
    
    def add_text(self, text: str) -> None:
        """Append text to the message."""
        if self.text:
            self.text += "\n" + text
        else:
            self.text = text
    
    def add_image(self, image: Union[str, bytes, BinaryIO], 
                content_type: Optional[str] = None) -> ImageResource:
        """Add an image to the message."""
        resource = ImageResource(image, content_type)
        self.resources.append(resource)
        return resource
    
    def add_audio(self, audio: Union[str, bytes, BinaryIO],
                content_type: Optional[str] = None,
                duration_seconds: Optional[float] = None) -> AudioResource:
        """Add audio to the message."""
        resource = AudioResource(audio, content_type, duration_seconds=duration_seconds)
        
        # If no audio is set as main audio yet, use this one
        if not self.has_audio:
            self.audio = resource
            self.has_audio = True
        else:
            self.resources.append(resource)
            
        return resource
    
    def add_document(self, document: Union[str, bytes, BinaryIO],
                   content_type: Optional[str] = None) -> DocumentResource:
        """Add a document to the message."""
        resource = DocumentResource(document, content_type)
        self.resources.append(resource)
        return resource
    
    def add_link(self, url: str, title: Optional[str] = None) -> LinkResource:
        """Add a web link to the message."""
        resource = LinkResource(url, title)
        self.resources.append(resource)
        return resource
    
    def get_images(self) -> List[ImageResource]:
        """Get all image resources in the message."""
        return [r for r in self.resources if isinstance(r, ImageResource)]
    
    def get_documents(self) -> List[DocumentResource]:
        """Get all document resources in the message."""
        return [r for r in self.resources if isinstance(r, DocumentResource)]
    
    def get_links(self) -> List[LinkResource]:
        """Get all link resources in the message."""
        return [r for r in self.resources if isinstance(r, LinkResource)]
    
    def get_all_text(self) -> str:
        """Get all text from the message and text resources."""
        texts = [self.text] if self.text else []
        
        for resource in self.resources:
            if isinstance(resource, TextResource):
                texts.append(resource.get_text())
                
        return "\n\n".join([t for t in texts if t])
    
    def __repr__(self) -> str:
        parts = []
        if self.text:
            text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
            parts.append(f"text='{text_preview}'")
        if self.has_audio:
            parts.append("has_audio=True")
        if self.resources:
            parts.append(f"resources={len(self.resources)}")
        
        return f"<UserMessage id={self.id} {' '.join(parts)}>"
  

