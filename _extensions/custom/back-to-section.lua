local function stringify(x)
  if x == nil then
    return ""
  end
  return pandoc.utils.stringify(x)
end

function Pandoc(doc)
  if not quarto.doc.is_format("html") then
    return doc
  end

  local href = stringify(doc.meta.section_href)
  local title = stringify(doc.meta.section_title)

  if href == "" then
    return doc
  end

  if title == "" then
    title = "la sección"
  end

  local html = string.format(
    '<div class="back-to-section"><a href="%s">← Volver a %s</a></div>',
    href,
    title
  )

  table.insert(doc.blocks, 1, pandoc.RawBlock("html", html))
  return doc
end