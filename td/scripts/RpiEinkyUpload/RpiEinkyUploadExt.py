
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
			self.upload_image_top(self.image)
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
	
	def clear_display(self):
		"""Clear the e-ink display by removing all files from Pi (legacy method)"""
		try:
			debug("ðŸ§¹ Clearing display by removing all files from Pi...")
			
			# Use cleanup with keep_count=0 to remove all files
			# This effectively "clears" the display since no files remain
			self.cleanup_pi_files(keep_count=0)
			
			debug(f"Display cleared by removing all Pi files")
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
			temp_file = self._get_temp_file_path("temp_eink_top")
			
			self.movieFileOut.par.file.expr = f'"{temp_file}" + me.fileSuffix'

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
	
	def onNewFileFoundTable(self, dat):
		latestFilePath = self.latestFilePath
		debug(f"New file found: {latestFilePath}")
		self.upload_file(latestFilePath)

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
	
	def onParCleanlocalfolder(self):
		debug("Cleaning local folder")
		self.cleanup_local_temp()

	def onParCleanrpifolder(self):
		debug("Cleaning Pi folder")
		# Force cleanup by keeping only 1 file, or 0 to remove all
		self.cleanup_pi_files(keep_count=0)

	def cleanup_folders(self, keep_pi_files=10, clean_local_temp=True):
		"""Clean both local temp folder and Pi watched folder"""
		debug(f"ðŸ§¹ Starting folder cleanup...")
		
		results = {
			'local_temp_cleaned': False,
			'pi_files_cleaned': False,
			'local_files_removed': 0,
			'pi_files_removed': 0
		}
		
		# Clean local temp folder
		if clean_local_temp:
			results['local_files_removed'] = self.cleanup_local_temp()
			results['local_temp_cleaned'] = True
		
		# Clean Pi watched folder
		results['pi_files_removed'] = self.cleanup_pi_files(keep_pi_files)
		results['pi_files_cleaned'] = True
		
		debug(f"ðŸ§¹ Cleanup complete: {results}")
		return results
	
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
	
	
	def get_latest_pi_file(self):
		"""Get info about the latest file on Pi"""
		try:
			connection_id = self.webClient.request(
				f'{self.server_url}/latest_file',
				'GET'
			)
			
			debug(f"ðŸ“„ Getting latest Pi file info...")
			
			# Handle response
			self._handle_response("Get latest Pi file", connection_id)
			
			return True
			
		except Exception as e:
			debug(f"âŒ Get latest Pi file error: {e}")
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
	
	def CleanupAll(self, keep_files=1):
		"""Clean both local temp and Pi folders"""
		return self.cleanup_folders(keep_pi_files=keep_files, clean_local_temp=True)
	
	def CleanupAllAggressive(self):
		"""Remove ALL files from both local temp and Pi folders"""
		return self.cleanup_folders(keep_pi_files=0, clean_local_temp=True)
	
	def CleanupLocalOnly(self):
		"""Clean only local temp folder"""
		return self.cleanup_local_temp()
	
	def CleanupPiOnly(self, keep_files=1):
		"""Clean only Pi watched folder"""
		return self.cleanup_pi_files(keep_files)
	
	def onParCleardisplay(self):
		debug("Clearing display screen")
		self.clear_display_screen()

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
	
	def onResponse(self, statusCode, headerDict, data, id):
		"""Handle WebclientDAT response callback"""
		# This method should be called by the WebclientDAT's onResponse callback
		# response object contains: id, url, statusCode, statusReason, data
		try:
			if statusCode['code'] == 200:
				debug(f"âœ… Request successful (ID: {id})")
				if data:
					try:
						response_data = json.loads(data)
						if 'filename' in response_data:
							debug(f"   File: {response_data['filename']}")
						if 'message' in response_data:
							debug(f"   Message: {response_data['message']}")
					except:
						debug(f"   Response: {data}")
				
				ui.clipboard = f"Request successful\n{data}"
			else:
				debug(f"âŒ Request failed: {statusCode['code']} - {headerDict}")
				ui.clipboard = f"Request failed: {statusCode['code']} - {headerDict}"
		except Exception as e:
			debug(e)
			debug(f"âŒ Response handling error: {e}")
			ui.clipboard = f"Response handling error: {e}"


