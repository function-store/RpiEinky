
import json
import os
from pathlib import Path

CustomParHelper: CustomParHelper = next(d for d in me.docked if 'ExtUtils' in d.tags).mod('CustomParHelper').CustomParHelper # import
###

class RpiEinkyUploadExt:
	def __init__(self, ownerComp):
		CustomParHelper.Init(self, ownerComp, enable_properties=True, enable_callbacks=True)
		self.ownerComp = ownerComp
		self.webClient : webclientDAT = self.ownerComp.op('webclient1')
		self.movieFileOut : moviefileoutTOP = self.ownerComp.op('moviefileout1')
		
		
	@property
	def image(self):
		return self.ownerComp.op('null_img')

	@property
	def isOnCook(self):
		return self.ownerComp.par.Oncook.eval()

	@property
	def tempFolder(self):
		temp_folder = self.ownerComp.par.Tempfolder.eval()
		return temp_folder if temp_folder else None
		
	@property
	def pi_address(self):
		return self.ownerComp.par.Piaddress.eval()
	
	@property
	def port(self):
		return self.ownerComp.par.Port.eval()

	@property
	def server_url(self):
		return f"http://{self.pi_address}:{self.port}"
	
	def _get_temp_file_path(self, filename):
		"""Get a temporary file path, using tempFolder or VFS"""
		if self.tempFolder:
			return f"{self.tempFolder}/{filename}"
		else:
			# Use Virtual File System if no temp folder specified
			return f"vfs://{filename}"

	def onParSend(self):
		"""Handle the Send parameter - upload current image"""
		if hasattr(self.image, 'save'):
			# Upload current image directly
			self.upload_image_top(self.image)
		else:
			debug("No image available to upload")
	
	def upload_file(self, filepath):
		"""Upload a file to the e-ink display"""
		try:
			if not os.path.exists(filepath):
				debug(f"File not found: {filepath}")
				return False
			
			filename = os.path.basename(filepath)
			
			# Use WebclientDAT request method for file upload
			# Note: uploadFile parameter only works with PUT method
			connection_id = self.webClient.request(
				f'{self.server_url}/upload',
				'PUT',
				header={'X-Filename': filename},
				uploadFile=filepath
			)
			
			debug(f"Uploading file: {filename} (connection: {connection_id})")
			
			# Handle response
			self._handle_response("File upload", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"File upload error: {e}")
			return False
	
	def upload_text(self, content, filename="touchdesigner_text.txt"):
		"""Upload text content to the e-ink display"""
		try:
			if not content:
				debug("No text content to upload")
				return False
			
			# Prepare JSON data
			data = {
				'content': content,
				'filename': filename
			}
			
			# Use WebclientDAT request method for text upload
			connection_id = self.webClient.request(
				f'{self.server_url}/upload_text',
				'POST',
				header={'Content-Type': 'application/json'},
				data=json.dumps(data)
			)
			
			debug(f"Uploading text content... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Text upload", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Text upload error: {e}")
			return False
	
	def clear_display(self):
		"""Clear the e-ink display"""
		try:
			# Use WebclientDAT request method for clear display
			connection_id = self.webClient.request(
				url=f'{self.server_url}/clear_display',
				method='POST'
			)
			
			debug(f"Clearing display... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Clear display", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Clear display error: {e}")
			return False
	
	def check_status(self):
		"""Check the server status"""
		try:
			# Use WebclientDAT request method for status check
			connection_id = self.webClient.request(
				url=f'{self.server_url}/status',
				method='GET'
			)
			
			debug(f"Checking server status... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Status check", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Status check error: {e}")
			return False
	
	def upload_image_top(self, top_op):
		"""Upload an image from a TOP operator"""
		try:
			if not top_op:
				debug("No TOP operator provided")
				return False
			
			# Get temp file path
			temp_file = self._get_temp_file_path("temp_eink_top.bmp")
			
			self.movieFileOut.par.file = temp_file

			# Save TOP to temp file
			self.movieFileOut.par.addframe.pulse()

			# TODO: wait for file to be saved
			# saved_path = top_op.save(temp_file, asynchronous=True,createFolders=True, quality=0.9)
			saved_path = Path(project.folder) / temp_file

			debug(f"Saved {top_op} to {saved_path}; {temp_file}")
			# waiting for file to be saved
			
			# # Upload the file
			# result = self.upload_file(saved_path)
			
			# # Clean up temp file (only if not using VFS)
			# if not temp_file.startswith("vfs://"):
			# 	try:
			# 		os.remove(saved_path)
			# 	except:
			# 		pass
			
			# return result
			
		except Exception as e:
			debug(f"TOP upload error: {e}")
			return False
	

	def onNewFileFound(self, info):
		path = info.path
		debug(f"New file found: {path}")
		try:
			debug(f"Uploading file: {path}")
			self.upload_file(path)
		except Exception as e:
			debug(f"File upload error: {e}")
			return False

	def upload_file_dialog(self):
		"""Open file dialog and upload selected file"""
		try:
			filepath = ui.chooseFile(
				load=True, 
				fileTypes=['jpg', 'png', 'txt', 'pdf', 'bmp', 'gif']
			)
			
			if filepath:
				return self.upload_file(filepath)
			else:
				debug("No file selected")
				return False
				
		except Exception as e:
			debug(f"File dialog error: {e}")
			return False
	
	def onParUploadfile(self):
		debug("Uploading file")
		self.upload_file_dialog()

	def upload_text_as_file(self, content, filename="text_content.txt"):
		"""Upload text content as a file (alternative to upload_text)"""
		try:
			if not content:
				debug("No text content to upload")
				return False
			
			# Create temp file with text content
			temp_file = self._get_temp_file_path(filename)
			
			# Write text content to file
			with open(temp_file, 'w', encoding='utf-8') as f:
				f.write(content)
			
			# Upload the file
			result = self.upload_file(temp_file)
			
			# Clean up temp file (only if not using VFS)
			if not temp_file.startswith("vfs://"):
				try:
					os.remove(temp_file)
				except:
					pass
			
			return result
			
		except Exception as e:
			debug(f"Text file upload error: {e}")
			return False
	
	def _handle_response(self, operation_name, connection_id):
		"""Handle WebclientDAT response using onResponse callback"""
		debug(f"Request sent for {operation_name} with connection ID: {connection_id}")
		# Note: Response handling should be implemented in the onResponse callback
		# of the WebclientDAT, using the connection_id to match requests
	
	# Convenience methods for common operations
	def SendCurrentImage(self):
		"""Send the current image from the image property"""
		self.onParSend()
	
	def SendTextMessage(self, message):
		"""Send a text message to the display"""
		return self.upload_text(message, "message.txt")
	
	def SendStatusUpdate(self, status_text):
		"""Send a status update to the display"""
		return self.upload_text(status_text, "status.txt")
	
	def SendRenderTop(self, top_op):
		"""Send a specific TOP to the display"""
		if top_op:
			return self.upload_image_top(top_op)
		else:
			debug(f"TOP '{top_op}' not found")
			return False
	
	# Properties for easy access
	@property
	def is_connected(self):
		"""Check if we can connect to the server"""
		try:
			self.check_status()
			return True
		except:
			return False
	
	def onResponse(self, statusCode, headerDict, data, id):
		"""Handle WebclientDAT response callback"""
		# This method should be called by the WebclientDAT's onResponse callback
		# response object contains: id, url, statusCode, statusReason, data
		try:
			if statusCode == 200:
				debug(f"✅ Request successful (ID: {id})")
				if data:
					try:
						response_data = json.loads(data)
						if 'filename' in response_data:
							debug(f"   File: {response_data['filename']}")
						if 'message' in response_data:
							debug(f"   Message: {response_data['message']}")
					except:
						debug(f"   Response: {data}")
				
				# Update status display if available
				status_display = self.ownerComp.op('status_display')
				if status_display:
					status_display.text = f"Request successful\n{data}"
			else:
				debug(f"❌ Request failed: {statusCode} - {headerDict['statusReason']}")
				status_display = self.ownerComp.op('status_display')
				if status_display:
					status_display.text = f"Request failed: {statusCode}"
		except Exception as e:
			debug(f"❌ Response handling error: {e}")


