import bleach

ALLOWED_TAGS=[
    "p","br","strong","em","code","pre","ul","ol","ol","li","h3","h4","blockquote","a"
    
]
ALLOWED_ATTRIBUTES={
    "a":["href","title","rel"]
}

def sanitize_post_content(value):
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
def sanitize_plain(value):
    return bleach.clean(value,tags=[],strip=True)