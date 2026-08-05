// WXML tag balance checker (dev tool, not part of the mini program)
const fs = require('fs')
const path = require('path')

const root = process.argv[2] || '.'
const files = []
function walk(d) {
  for (const f of fs.readdirSync(d)) {
    const p = path.join(d, f)
    const s = fs.statSync(p)
    if (s.isDirectory()) walk(p)
    else if (f.endsWith('.wxml')) files.push(p)
  }
}
walk(root)

const tags = ['view', 'block', 'swiper', 'swiper-item', 'image', 'text', 'button', 'input', 'video', 'empty', 'scroll-view']
let bad = 0
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8')
  for (const t of tags) {
    const open = (src.match(new RegExp('<' + t + '[\\s>]', 'g')) || []).length
    const close = (src.match(new RegExp('</' + t + '>', 'g')) || []).length
    const selfClose = (src.match(new RegExp('<' + t + '[^>]*/>', 'g')) || []).length
    if (open !== close + selfClose) {
      bad++
      console.log(f, '<' + t + '> open=' + open + ' close=' + close + ' selfclose=' + selfClose)
    }
  }
}
console.log(bad === 0 ? 'ALL WXML TAGS BALANCED (' + files.length + ' files)' : 'CHECK FAILED')
process.exit(bad ? 1 : 0)
