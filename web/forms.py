"""
Django forms for the web application.
"""

from django import forms
from archive.models import Shortcode


class CreateArchiveForm(forms.Form):
    """Form for creating a new archive."""
    
    url = forms.URLField(
        max_length=2000,
        widget=forms.URLInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'https://example.com/article',
            'required': True,
        }),
        help_text="Enter the complete URL including http:// or https://"
    )
    
    text_fragment = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Important quote or text to highlight',
        }),
        help_text="Specify a text fragment to highlight in the archived page"
    )
    
    archive_method = forms.ChoiceField(
        choices=[
            ('singlefile', 'SingleFile - Complete page with embedded resources'),
            ('archivebox', 'ArchiveBox - Multiple formats (HTML, PDF, screenshot)'),
            ('both', 'Both Methods - Maximum coverage'),
        ],
        initial='singlefile',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text="Choose how you want the page to be archived"
    )
    
    custom_shortcode = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your custom shortcode',
            'pattern': '[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+',
            'title': 'Only Base58 characters allowed (no I, l, 0, O)',
        }),
        help_text="Choose your own shortcode. Leave blank to auto-generate."
    ) 