"""
TouchDesigner E-ink Display Control Script
Copy this script into a Text DAT in TouchDesigner and run it to build the interface.

Instructions:
1. Open TouchDesigner
2. Create a new Text DAT
3. Copy this entire script into the Text DAT
4. Set the Text DAT to Python
5. Run the script to build the interface
6. Update the PI_IP variable to your Raspberry Pi's IP address

This script uses WebclientDAT for proper HTTP communication instead of the older webDAT.
WebclientDAT provides better control over HTTP requests, responses, and file uploads.
"""

import json

# Configuration - UPDATE THIS TO YOUR RASPBERRY PI'S IP ADDRESS
PI_IP = "192.168.1.100"
PI_PORT = 5000

def build_eink_interface():
    """Build the TouchDesigner interface for e-ink display control"""
    
    # Find the container to build in (use current container)
    container = parent()
    
    # Clear existing components (optional)
    # for child in container.children:
    #     child.destroy()
    
    # Create WebclientDATs for different endpoints
    
    # 1. File Upload WebclientDAT
    web_upload = container.create(webclientDAT, 'web_upload')
    web_upload.par.url = f'http://{PI_IP}:{PI_PORT}/upload'
    web_upload.par.httpmethod = 'POST'
    web_upload.par.request = False
    
    # 2. Text Upload WebclientDAT
    web_text = container.create(webclientDAT, 'web_text')
    web_text.par.url = f'http://{PI_IP}:{PI_PORT}/upload_text'
    web_text.par.httpmethod = 'POST'
    web_text.par.httpheaders = 'Content-Type: application/json'
    web_text.par.request = False
    
    # 3. Clear Display WebclientDAT
    web_clear = container.create(webclientDAT, 'web_clear')
    web_clear.par.url = f'http://{PI_IP}:{PI_PORT}/clear_display'
    web_clear.par.httpmethod = 'POST'
    web_clear.par.request = False
    
    # 4. Status Check WebclientDAT
    web_status = container.create(webclientDAT, 'web_status')
    web_status.par.url = f'http://{PI_IP}:{PI_PORT}/status'
    web_status.par.httpmethod = 'GET'
    web_status.par.request = False
    
    # Create Text DATs for content
    
    # 5. Text Content Input
    text_content = container.create(textDAT, 'text_content')
    text_content.text = "Hello from TouchDesigner!\nThis will appear on the e-ink display."
    
    # 6. Status Display
    status_display = container.create(textDAT, 'status_display')
    status_display.text = "Server status will appear here"
    
    # Create UI Panel
    ui_panel = container.create(panelCOMP, 'eink_control_panel')
    ui_panel.par.w = 800
    ui_panel.par.h = 600
    
    # Create UI elements inside the panel
    panel_container = ui_panel
    
    # Upload File Button
    upload_btn = panel_container.create(buttonCOMP, 'upload_file_btn')
    upload_btn.par.text = "Upload File"
    upload_btn.par.w = 150
    upload_btn.par.h = 50
    upload_btn.par.alignx = 'left'
    upload_btn.par.aligny = 'top'
    upload_btn.par.x = 50
    upload_btn.par.y = 50
    
    # Upload Text Button
    upload_text_btn = panel_container.create(buttonCOMP, 'upload_text_btn')
    upload_text_btn.par.text = "Upload Text"
    upload_text_btn.par.w = 150
    upload_text_btn.par.h = 50
    upload_text_btn.par.alignx = 'left'
    upload_text_btn.par.aligny = 'top'
    upload_text_btn.par.x = 220
    upload_text_btn.par.y = 50
    
    # Clear Display Button
    clear_btn = panel_container.create(buttonCOMP, 'clear_display_btn')
    clear_btn.par.text = "Clear Display"
    clear_btn.par.w = 150
    clear_btn.par.h = 50
    clear_btn.par.alignx = 'left'
    clear_btn.par.aligny = 'top'
    clear_btn.par.x = 390
    clear_btn.par.y = 50
    
    # Status Button
    status_btn = panel_container.create(buttonCOMP, 'status_btn')
    status_btn.par.text = "Check Status"
    status_btn.par.w = 150
    status_btn.par.h = 50
    status_btn.par.alignx = 'left'
    status_btn.par.aligny = 'top'
    status_btn.par.x = 560
    status_btn.par.y = 50
    
    # Text Area for Content
    text_area = panel_container.create(textareaDAT, 'text_area')
    text_area.par.w = 600
    text_area.par.h = 200
    text_area.par.x = 50
    text_area.par.y = 150
    text_area.text = text_content.text
    
    # Status Display Area
    status_area = panel_container.create(fieldCOMP, 'status_area')
    status_area.par.w = 600
    status_area.par.h = 150
    status_area.par.x = 50
    status_area.par.y = 400
    status_area.par.text = "Server responses will appear here"
    
    print("E-ink display interface created successfully!")
    print(f"Server IP set to: {PI_IP}:{PI_PORT}")
    print("Don't forget to update the IP address if needed!")
    
    return {
        'web_upload': web_upload,
        'web_text': web_text,
        'web_clear': web_clear,
        'web_status': web_status,
        'text_content': text_content,
        'status_display': status_display,
        'ui_panel': ui_panel
    }

# Response handler for WebclientDAT operations
def handle_response(web_client, operation_name, delay_frames=30):
    """Generic response handler for WebclientDAT operations"""
    def check_response():
        try:
            response_code = web_client.par.responsecode
            response_text = web_client.text
            
            if response_code == 200:
                print(f"✅ {operation_name} successful")
                if response_text:
                    try:
                        response_data = json.loads(response_text)
                        if 'filename' in response_data:
                            print(f"   File: {response_data['filename']}")
                        if 'message' in response_data:
                            print(f"   Message: {response_data['message']}")
                    except:
                        print(f"   Response: {response_text}")
                
                # Update status display if available
                if op('status_area'):
                    op('status_area').par.text = f"{operation_name} successful\n{response_text}"
            else:
                print(f"❌ {operation_name} failed: {response_code}")
                if op('status_area'):
                    op('status_area').par.text = f"{operation_name} failed: {response_code}"
        except Exception as e:
            print(f"❌ {operation_name} response error: {e}")
    
    # Schedule response check
    run(check_response, delayFrames=delay_frames)

# Button callback functions
def upload_file_callback():
    """Handle file upload button click"""
    try:
        # Use file dialog to select file
        filepath = ui.chooseFile(load=True, fileTypes=['jpg', 'png', 'txt', 'pdf', 'bmp', 'gif'])
        if not filepath:
            return
        
        # Get filename
        import os
        filename = os.path.basename(filepath)
        
        # Use WebclientDAT for file upload
        web_client = op('web_upload')
        
        # Set up file upload using WebclientDAT
        web_client.par.url = f'http://{PI_IP}:{PI_PORT}/upload'
        web_client.par.httpmethod = 'POST'
        
        # Add file to form data
        web_client.par.formdata = f'file={filepath}'
        
        # Trigger request
        web_client.request()
        
        print(f"Uploading file: {filename}")
        
        # Handle response
        handle_response(web_client, "File upload")
        
    except Exception as e:
        print(f"File upload error: {e}")

def upload_text_callback():
    """Handle text upload button click"""
    try:
        # Get text content from text area
        text_content = op('text_area').text if op('text_area') else op('text_content').text
        
        if not text_content:
            print("No text content to upload")
            return
        
        # Prepare JSON data
        data = {
            'content': text_content,
            'filename': 'touchdesigner_text.txt'
        }
        
        # Use WebclientDAT for text upload
        web_client = op('web_text')
        web_client.par.url = f'http://{PI_IP}:{PI_PORT}/upload_text'
        web_client.par.httpmethod = 'POST'
        web_client.par.httpheaders = 'Content-Type: application/json'
        web_client.par.postdata = json.dumps(data)
        
        # Trigger request
        web_client.request()
        
        print("Uploading text content...")
        
        # Handle response
        handle_response(web_client, "Text upload")
        
    except Exception as e:
        print(f"Text upload error: {e}")

def clear_display_callback():
    """Handle clear display button click"""
    try:
        web_client = op('web_clear')
        web_client.par.url = f'http://{PI_IP}:{PI_PORT}/clear_display'
        web_client.par.httpmethod = 'POST'
        
        # Trigger request
        web_client.request()
        
        print("Clearing display...")
        
        # Handle response
        handle_response(web_client, "Clear display")
        
    except Exception as e:
        print(f"Clear display error: {e}")

def check_status_callback():
    """Handle status check button click"""
    try:
        web_client = op('web_status')
        web_client.par.url = f'http://{PI_IP}:{PI_PORT}/status'
        web_client.par.httpmethod = 'GET'
        
        # Trigger request
        web_client.request()
        
        print("Checking server status...")
        
        # Handle response
        handle_response(web_client, "Status check")
        
    except Exception as e:
        print(f"Status check error: {e}")

# Advanced upload function using requests (if available)
def upload_file_advanced(filepath):
    """Advanced file upload using requests library"""
    try:
        import requests
        
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = requests.post(f'http://{PI_IP}:{PI_PORT}/upload', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload successful: {result['filename']}")
            return True
        else:
            print(f"Upload failed: {response.text}")
            return False
            
    except ImportError:
        print("Requests library not available, using Web DAT instead")
        return False
    except Exception as e:
        print(f"Upload error: {e}")
        return False

def upload_text_advanced(content, filename="touchdesigner.txt"):
    """Advanced text upload using requests library"""
    try:
        import requests
        
        data = {
            'content': content,
            'filename': filename
        }
        
        response = requests.post(
            f'http://{PI_IP}:{PI_PORT}/upload_text',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Text upload successful: {result['filename']}")
            return True
        else:
            print(f"Text upload failed: {response.text}")
            return False
            
    except ImportError:
        print("Requests library not available, using Web DAT instead")
        return False
    except Exception as e:
        print(f"Text upload error: {e}")
        return False

# Run the builder
if __name__ == "__main__":
    components = build_eink_interface()
    
    # Print instructions
    print("\n" + "="*60)
    print("TOUCHDESIGNER E-INK DISPLAY CONTROLLER")
    print("="*60)
    print(f"Server IP: {PI_IP}:{PI_PORT}")
    print("\nTo use:")
    print("1. Start the upload server on your Pi: python upload_server.py")
    print("2. Update PI_IP variable to your Pi's IP address")
    print("3. Use the buttons to upload files and text")
    print("4. Check status to verify server connection")
    print("\nComponents created:")
    for name, comp in components.items():
        print(f"  - {name}: {comp}")
    
    print("\nButton Scripts:")
    print("- upload_file_btn: Add script -> upload_file_callback()")
    print("- upload_text_btn: Add script -> upload_text_callback()")
    print("- clear_display_btn: Add script -> clear_display_callback()")
    print("- status_btn: Add script -> check_status_callback()")
    print("\nWebclientDAT Benefits:")
    print("- Better file upload support with formdata")
    print("- Proper HTTP response handling")
    print("- More reliable than webDAT for HTTP requests")
    print("- Built-in support for multipart form data")
    print("="*60) 