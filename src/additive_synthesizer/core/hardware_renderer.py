import ctypes
import math

import numpy as np
import pygame
from OpenGL.GL import (
    # Constants
    GL_ARRAY_BUFFER,
    GL_CLAMP_TO_EDGE,
    GL_COLOR_BUFFER_BIT,
    GL_COMPILE_STATUS,
    GL_FALSE,
    GL_FLOAT,
    GL_FRAGMENT_SHADER,
    GL_LINEAR,
    GL_LINK_STATUS,
    GL_RGBA,
    GL_STATIC_DRAW,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_TRIANGLE_STRIP,
    GL_UNSIGNED_BYTE,
    GL_VERTEX_SHADER,
    glActiveTexture,
    glAttachShader,
    glBindBuffer,
    glBindTexture,
    glBufferData,
    glClear,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteShader,
    glDrawArrays,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenTextures,
    glGetAttribLocation,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glTexImage2D,
    glTexParameteri,
    glTexSubImage2D,
    glUniform1f,
    # Functions
    glUseProgram,
    glVertexAttribPointer,
    glViewport,
)


class HardwareRenderer:
    def __init__(self, physical_size, logical_size, rotation_angle=90):
        self.phys_w, self.phys_h = physical_size
        self.log_w, self.log_h = logical_size

        self.screen = pygame.display.set_mode(
            physical_size,
            pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.HWSURFACE,
        )

        self.program = self._compile_shaders()
        glUseProgram(self.program)

        # Each row is one vertex: (x, y, u, v)
        # NDC coords range [-1, 1]; UV origin is top-left in OpenGL convention.
        # fmt: off
        vertices = np.array([
            -1.0, -1.0,  1.0, 0.0,  # bottom-left  NDC → UV (1, 0)
             1.0, -1.0,  0.0, 0.0,  # bottom-right NDC → UV (0, 0)
            -1.0,  1.0,  1.0, 1.0,  # top-left     NDC → UV (1, 1)
             1.0,  1.0,  0.0, 1.0,  # top-right    NDC → UV (0, 1)
        ], dtype=np.float32)
        # fmt: on
        vertex_data = vertices.tobytes()

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, len(vertex_data), vertex_data, GL_STATIC_DRAW)

        stride = 4 * 4
        pos_loc = glGetAttribLocation(self.program, "a_position")
        tex_loc = glGetAttribLocation(self.program, "a_texCoord")

        glEnableVertexAttribArray(pos_loc)
        glVertexAttribPointer(
            pos_loc, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0)
        )

        glEnableVertexAttribArray(tex_loc)
        glVertexAttribPointer(
            tex_loc, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8)
        )

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # Allocate memory once
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            self.log_w,
            self.log_h,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            None,
        )

        rads = math.radians(rotation_angle)
        rot_loc = glGetUniformLocation(self.program, "u_rotation")
        glUniform1f(rot_loc, rads)

        glViewport(0, 0, self.phys_w, self.phys_h)

    def render(self, surface):
        """
        Uploads the pygame surface to GPU via Zero-Copy ctypes wrapper.
        """
        view = surface.get_view("1")

        data_len = self.log_w * self.log_h * 4  # 4 bytes per pixel (RGBA)
        texture_data = (ctypes.c_ubyte * data_len).from_buffer(view)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            self.log_w,
            self.log_h,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            texture_data,
        )

        glClear(GL_COLOR_BUFFER_BIT)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        pygame.display.flip()

    def _compile_shaders(self):
        vertex_src = """
            attribute vec2 a_position;
            attribute vec2 a_texCoord;
            varying vec2 v_texCoord;
            uniform float u_rotation;
    
            void main() {
                float c = cos(u_rotation);
                float s = sin(u_rotation);
                float x = a_position.x * c - a_position.y * s;
                float y = a_position.x * s + a_position.y * c;
                gl_Position = vec4(x, y, 0.0, 1.0);
                v_texCoord = a_texCoord;
            }
            """

        fragment_src = """
            precision mediump float;
            varying vec2 v_texCoord;
            uniform sampler2D u_texture;
    
            void main() {
                // Read the texture color
                vec4 color = texture2D(u_texture, v_texCoord);
                
                // Swap Red and Blue components using swizzling (.bgra)
                // Input memory is BGRA, but GL treats it as RGBA.
                // So: 
                // GL's 'r' channel holds Blue.
                // GL's 'b' channel holds Red.
                // We output (b, g, r, a) to put them back in correct order.
                
                gl_FragColor = color.bgra;
            }
            """

        def compile(type, source):
            shader = glCreateShader(type)
            glShaderSource(shader, source)
            glCompileShader(shader)
            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader))
            return shader

        vs = compile(GL_VERTEX_SHADER, vertex_src)
        fs = compile(GL_FRAGMENT_SHADER, fragment_src)

        prog = glCreateProgram()
        glAttachShader(prog, vs)
        glAttachShader(prog, fs)
        glLinkProgram(prog)
        if not glGetProgramiv(prog, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(prog))

        # The driver has copied everything it needs into the program object;
        # the individual shader handles are now orphaned GPU allocations.
        # Mark them for deletion so the driver can free them immediately.
        glDeleteShader(vs)
        glDeleteShader(fs)

        return prog
