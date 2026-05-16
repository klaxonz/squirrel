(() => {
  const originalAttachShadow = Element.prototype.attachShadow
  Element.prototype.attachShadow = function attachShadow(init) {
    const shadowRoot = originalAttachShadow.call(this, init)
    this.shadowRootUnl = shadowRoot
    return shadowRoot
  }
})()
