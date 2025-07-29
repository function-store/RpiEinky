
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
		self.movieFileIn : moviefileinTOP = self.ownerComp.op('moviefilein1')
		
		
	@property
	def image(self):
		return self.ownerComp.op('null_img')

	@property
	def latestFilePath(self):
		sorty = self.ownerComp.op('sort1')
		path = sorty[1,'path'].val
		return path

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
			self.saveImageToDisk(self.image)
		else:
			debug("No image available to upload")
	
	def upload_file(self, filepath):
		"""Upload a file to the e-ink display"""
		try:
			if not os.path.exists(filepath):
				debug(f"File not found: {filepath}")
				return False
			#self.movieFileIn.par.file.val = filepath
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
	
	def clear_display_screen(self):
		"""Actually clear the e-ink display screen"""
		try:
			# Use WebclientDAT request method to clear the actual display
			connection_id = self.webClient.request(
				f'{self.server_url}/clear_screen',
				'POST'
			)
			
			debug(f"ðŸ–¥ï¸ Clearing e-ink display screen... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Clear display screen", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Clear display screen error: {e}")
			return False
	

	
	def check_status(self):
		"""Check the server status"""
		try:
			# Use WebclientDAT request method for status check
			connection_id = self.webClient.request(
				f'{self.server_url}/status',
				'GET'
			)
			
			debug(f"Checking server status... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Status check", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Status check error: {e}")
			return False
	
	def get_display_info(self):
		"""Get display information including resolution"""
		try:
			# Use WebclientDAT request method for display info
			connection_id = self.webClient.request(
				f'{self.server_url}/display_info',
				'GET'
			)
			
			debug(f"Getting display info... (connection: {connection_id})")
			
			# Handle response
			self._handle_response("Display info", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"Display info error: {e}")
			return False
			
		
	
	
	def onWebClientConnect(self, webClientDAT, id):
		"""Called when WebclientDAT connection is established"""
		try:
			debug("📺 Getting display info on connect")
			# Just get display info once
			if self.evalGetinfoonconnect:
				self.get_display_info()
			
		except Exception as e:
			debug(f"❌ Connection handling error: {e}")
	
	def onWebClientDisconnect(self, webClientDAT, id):
		"""Called when WebclientDAT connection is closed"""
		debug("🔌 WebclientDAT disconnected")
	
	def onWebClientResponse(self, webClientDAT, statusCode, headerDict, data, id):
		"""Called when response is received from server"""
		try:
			if statusCode['code'] == 200:
				debug(f"✅ Request successful (ID: {id})")
				if data:
					try:
						response_data = json.loads(data)
						
						# Handle display info response
						if 'resolution' in response_data and 'display_type' in response_data:
							self._handle_display_info_response(response_data)
						# Handle other responses
						elif 'filename' in response_data:
							debug(f"   File: {response_data['filename']}")
						elif 'message' in response_data:
							debug(f"   Message: {response_data['message']}")
						else:
							debug(f"   Response: {data}")
							
					except:
						debug(f"   Response: {data}")
				
			else:
				debug(f"❌ Request failed: {statusCode['code']} - {headerDict}")
		except Exception as e:
			debug(e)
			debug(f"❌ Response handling error: {e}")
	
	def saveImageToDisk(self, top_op):
		"""Save an image from a TOP operator"""
		try:
			if not top_op:
				debug("No TOP operator provided")
				return False
			
			# Get temp file path
			temp_file = self._get_temp_file_path("temp_eink_top")
			debug(f"Saving {top_op} to {temp_file}")
			
			self.movieFileOut.par.file.expr = f'"{temp_file}" + me.fileSuffix'

			# Save TOP to temp file
			self.movieFileOut.par.addframe.pulse()

			# saved_path = top_op.save(temp_file, asynchronous=True,createFolders=True, quality=0.9)
			saved_path = Path(project.folder) / temp_file

			debug(f"Saved {top_op} to {saved_path}; {temp_file}")
			# waiting for file to be saved
			# will be handled by the onNewFileFoundTable callback
			
		except Exception as e:
			debug(f"TOP upload error: {e}")
			return False
	
	def onNewFileFoundTable(self, dat):
		latestFilePath = self.latestFilePath
		debug(f"New file found: {latestFilePath}")
		self.upload_file(latestFilePath)


	def upload_file_dialog(self):
		"""Open file dialog and upload selected file"""
		try:
			filepath = ui.chooseFile(
				load=True, 
				fileTypes=['jpg', 'png', 'txt', 'pdf', 'bmp', 'gif']
			)

			self.upload_file(filepath)
				
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
	
	def onParCleanlocalfolder(self):
		debug("Cleaning local folder")
		self.cleanup_local_temp()

	def onParCleanrpifolder(self):
		debug("Cleaning Pi folder")
		# Force cleanup by keeping only 1 file, or 0 to remove all
		self.cleanup_pi_files(keep_count=0)


	
	def cleanup_local_temp(self):
		"""Clean local temp folder"""
		try:
			if not self.tempFolder:
				debug("No temp folder specified - skipping local cleanup")
				return 0
			
			import os
			from pathlib import Path
			
			temp_path = Path(self.tempFolder)
			if not temp_path.exists():
				debug(f"Temp folder doesn't exist: {temp_path}")
				return 0
			
			# Remove all files in temp folder
			files_removed = 0
			for file in temp_path.glob('*'):
				if file.is_file():
					try:
						file.unlink()
						files_removed += 1
						debug(f"   Removed: {file.name}")
					except Exception as e:
						debug(f"   Failed to remove {file.name}: {e}")
			
			debug(f"ðŸ§¹ Local temp cleanup: removed {files_removed} files from {temp_path}")
			return files_removed
			
		except Exception as e:
			debug(f"âŒ Local temp cleanup error: {e}")
			return 0
	
	def cleanup_pi_files(self, keep_count=10):
		"""Clean Pi watched folder, keeping only recent files"""
		try:
			# Prepare JSON data
			data = {
				'keep_count': keep_count
			}
			
			# Use WebclientDAT request method for cleanup
			connection_id = self.webClient.request(
				f'{self.server_url}/cleanup_old_files',
				'POST',
				header={'Content-Type': 'application/json'},
				data=json.dumps(data)
			)
			
			debug(f"ðŸ§¹ Pi cleanup request sent (keep {keep_count} files)...")
			
			# Handle response
			self._handle_response("Pi files cleanup", connection_id)
			
			return keep_count  # Return the keep count for now
			
		except Exception as e:
			debug(f"âŒ Pi cleanup error: {e}")
			return 0
	
	

	def _handle_response(self, operation_name, connection_id):
		"""Handle WebclientDAT response using onResponse callback"""
		debug(f"Request sent for {operation_name} with connection ID: {connection_id}")
		# Note: Response handling should be implemented in the onResponse callback
		# of the WebclientDAT, using the connection_id to match requests
	

	
	def GetDisplayInfo(self):
		"""Get current display information"""
		return self.get_display_info()
	
	@property
	def display_resolution(self):
		"""Get current display resolution as tuple (width, height)"""
		width = self.ownerComp.par.Displayresw.eval()
		height = self.ownerComp.par.Displayresh.eval()
		return (width, height) if width and height else None
	
	@property
	def native_resolution(self):
		"""Get native display resolution as tuple (width, height)"""
		width = self.ownerComp.par.Nativeresw.eval()
		height = self.ownerComp.par.Nativeresh.eval()
		return (width, height) if width and height else None
	
	@property
	def display_type(self):
		"""Get current display type"""
		return self.ownerComp.par.Displaytype.eval()
	
	@property
	def display_orientation(self):
		"""Get current display orientation"""
		return self.ownerComp.par.Displayorientation.eval()
	
	@property
	def native_orientation(self):
		"""Get native display orientation"""
		return self.ownerComp.par.Nativeorientation.eval()
	
	@property
	def display_source(self):
		"""Get display info source"""
		return self.ownerComp.par.Displaysource.eval()

	def onParCleardisplay(self):
		debug("Clearing display screen")
		self.clear_display_screen()

	def onParGetdisplayinfo(self):
		"""Parameter callback for getting display info"""
		debug("Getting display info")
		self.get_display_info()

	def ClearDisplayScreen(self):
		"""Actually clear the e-ink display screen"""
		return self.clear_display_screen()
	
	
	# Properties for easy access
	@property
	def is_connected(self):
		"""Check if we can connect to the server"""
		try:
			self.check_status()
			return True
		except:
			return False
	

	
	def _handle_display_info_response(self, response_data):
		"""Handle display info response and store the data"""
		try:
			# Extract display info
			display_type = response_data.get('display_type', 'unknown')
			resolution = response_data.get('resolution', {})
			native_resolution = response_data.get('native_resolution', {})
			width = resolution.get('width', 0)
			height = resolution.get('height', 0)
			native_width = native_resolution.get('width', width)
			native_height = native_resolution.get('height', height)
			orientation = response_data.get('orientation', 'landscape')
			native_orientation = response_data.get('native_orientation', 'landscape')
			source = response_data.get('source', 'unknown')
			
			# Store display info in the component
			self.ownerComp.par.Displaytype = display_type
			self.ownerComp.par.Displayresw = width if orientation == 'landscape' else height
			self.ownerComp.par.Displayresh = height if orientation == 'landscape' else width
			self.ownerComp.par.Displayorientation = orientation
			# self.ownerComp.par.Nativeresw = native_width
			# self.ownerComp.par.Nativeresh = native_height
			# self.ownerComp.par.Nativeorientation = native_orientation
			# self.ownerComp.par.Displaysource = source
			
			# Log the display info
			debug(f"📺 Display Info: {display_type} ({width}×{height} {orientation})")
			debug(f"📺 Native: {native_width}×{native_height} {native_orientation} (source: {source})")
			
		except Exception as e:
			debug(f"❌ Display info parsing error: {e}")



