/**
 * Minimal PNG decoder (8-bit RGBA, non-interlaced) for visual pixel compare.
 * Avoids adding a new dependency for baseline checks.
 */

import zlib from 'node:zlib'

function readU32(buf, offset) {
  return buf.readUInt32BE(offset)
}

function paeth(a, b, c) {
  const p = a + b - c
  const pa = Math.abs(p - a)
  const pb = Math.abs(p - b)
  const pc = Math.abs(p - c)
  if (pa <= pb && pa <= pc) return a
  if (pb <= pc) return b
  return c
}

function unfilter(filterType, row, prev, bpp) {
  const out = Buffer.alloc(row.length)
  for (let i = 0; i < row.length; i += 1) {
    const x = row[i]
    const a = i >= bpp ? out[i - bpp] : 0
    const b = prev ? prev[i] : 0
    const c = prev && i >= bpp ? prev[i - bpp] : 0
    let val
    switch (filterType) {
      case 0:
        val = x
        break
      case 1:
        val = (x + a) & 0xff
        break
      case 2:
        val = (x + b) & 0xff
        break
      case 3:
        val = (x + ((a + b) >> 1)) & 0xff
        break
      case 4:
        val = (x + paeth(a, b, c)) & 0xff
        break
      default:
        throw new Error(`Unsupported PNG filter type ${filterType}`)
    }
    out[i] = val
  }
  return out
}

/**
 * @param {Buffer} buffer
 * @returns {{ width: number, height: number, data: Buffer }}
 */
export function decode(buffer) {
  if (!Buffer.isBuffer(buffer)) {
    buffer = Buffer.from(buffer)
  }
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  if (buffer.subarray(0, 8).compare(sig) !== 0) {
    throw new Error('Not a PNG')
  }

  let offset = 8
  let width = 0
  let height = 0
  let bitDepth = 0
  let colorType = 0
  const idat = []

  while (offset < buffer.length) {
    const length = readU32(buffer, offset)
    const type = buffer.toString('ascii', offset + 4, offset + 8)
    const data = buffer.subarray(offset + 8, offset + 8 + length)
    offset += 12 + length

    if (type === 'IHDR') {
      width = readU32(data, 0)
      height = readU32(data, 4)
      bitDepth = data[8]
      colorType = data[9]
      const compression = data[10]
      const filter = data[11]
      const interlace = data[12]
      if (bitDepth !== 8) throw new Error(`PNG bitDepth ${bitDepth} not supported`)
      if (colorType !== 2 && colorType !== 6) {
        throw new Error(`PNG colorType ${colorType} not supported (need RGB/RGBA)`)
      }
      if (compression !== 0 || filter !== 0) throw new Error('Unsupported PNG compression/filter method')
      if (interlace !== 0) throw new Error('Interlaced PNG not supported')
    } else if (type === 'IDAT') {
      idat.push(data)
    } else if (type === 'IEND') {
      break
    }
  }

  const compressed = Buffer.concat(idat)
  const inflated = zlib.inflateSync(compressed)
  const bpp = colorType === 6 ? 4 : 3
  const stride = width * bpp
  const rgba = Buffer.alloc(width * height * 4)
  let inPos = 0
  let prev = null

  for (let y = 0; y < height; y += 1) {
    const filterType = inflated[inPos]
    inPos += 1
    const row = inflated.subarray(inPos, inPos + stride)
    inPos += stride
    const recon = unfilter(filterType, row, prev, bpp)
    prev = recon
    for (let x = 0; x < width; x += 1) {
      const si = x * bpp
      const di = (y * width + x) * 4
      rgba[di] = recon[si]
      rgba[di + 1] = recon[si + 1]
      rgba[di + 2] = recon[si + 2]
      rgba[di + 3] = bpp === 4 ? recon[si + 3] : 255
    }
  }

  return { width, height, data: rgba }
}

export const PNG = { decode }
