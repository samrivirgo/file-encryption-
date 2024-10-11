from django.shortcuts import render, redirect
from .forms import FileUpload, CustomPasswordChangeForm
from .models import FileEncryption
from django.conf import settings
from django.http import HttpResponse,  HttpResponseForbidden
import base64
from django.contrib.auth import authenticate, login as auth_login, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def upload_file(request):
    success_message = None
    if request.method == 'POST':
        form = FileUpload(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['uploade_file']  

            # Read and encrypt the file content
            file_data = uploaded_file.read()
            encrypted_data = settings.CIPHER.encrypt(file_data)

            # Save the encrypted file in the database
            encrypted_file = FileEncryption(
                file_name=uploaded_file.name,
                encrypted_file=encrypted_data,  # Save encrypted binary data
            )
            encrypted_file.save()

            success_message = "File uploaded and encrypted successfully!"

    else:
        form = FileUpload()

    return render(request, 'core/upload.html', {'form': form, 'success_message': success_message})

def download_file(request, file_id):
    try:
        encrypted_file = FileEncryption.objects.get(id=file_id)

        # Decrypt the file content
        decrypted_data = settings.CIPHER.decrypt(encrypted_file.encrypted_file)

        # Send the decrypted file as an HTTP response
        response = HttpResponse(decrypted_data, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{encrypted_file.file_name}"'

        return response
    except FileEncryption.DoesNotExist:
        return HttpResponse('File not found', status=404)

def list_uploaded_files(request):
    # Fetch all uploaded files from the database
    files = FileEncryption.objects.all()
    return render(request, 'core/file_list.html', {'files': files})

from django.http import HttpResponse, HttpResponseForbidden
from .models import FileEncryption
import base64

# Password protection for viewing encrypted or decrypted files
def view_encrypted_file(request, file_id):
    password = request.GET.get('password')  # Get password from query params

    try:
        encrypted_file = FileEncryption.objects.get(id=file_id)

        # Get the encrypted content
        encrypted_data = encrypted_file.encrypted_file

        # Check if password is correct
        if password == '123':
            # Decrypt the content
            decrypted_data = settings.CIPHER.decrypt(encrypted_data)
            
            # Detect if the file is text or binary and handle accordingly
            try:
                # Try to decode as UTF-8 (text file)
                decoded_data = decrypted_data.decode('utf-8')
                return HttpResponse(f"<pre>{decoded_data}</pre>", content_type='text/plain')
            except UnicodeDecodeError:
                # If decoding fails, assume it's a binary file (like image, PDF, etc.)
                response = HttpResponse(decrypted_data, content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{encrypted_file.file_name}"'
                return response
        else:
            # If password is incorrect, show encrypted content (in base64)
            encoded_data = base64.b64encode(encrypted_data).decode('utf-8')
            return HttpResponse(f"<pre>{encoded_data}</pre>", content_type='text/plain')

    except FileEncryption.DoesNotExist:
        return HttpResponse('File not found', status=404)



def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)  
                return redirect('home')  # Redirect home page
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login after signup
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            user = password_form.save()
            messages.success(request, "Your password has been successfully updated!")
            return redirect('profile')  # Redirect to profile page after successful password change
    else:
        password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'core/profile.html', {'password_form': password_form})